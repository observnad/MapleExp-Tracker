const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const mimeTypes = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  if (reqPath === '/') reqPath = '/index.html';
  const filePath = path.join(__dirname, '..', reqPath);

  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const ext = path.extname(filePath);
    res.writeHead(200, {
      'Content-Type': mimeTypes[ext] || 'application/octet-stream',
      'Cache-Control': 'no-store, no-cache, must-revalidate'
    });
    fs.createReadStream(filePath).pipe(res);
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

server.listen(8082, async () => {
  console.log('HTTP Server listening on http://localhost:8082');

  const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const chromeProc = spawn(chromePath, [
    '--headless=new',
    '--remote-debugging-port=9224',
    '--disable-gpu',
    '--disable-cache',
    '--no-first-run',
    '--no-default-browser-check',
    'http://localhost:8082/index.html'
  ]);

  let targetWsUrl = null;
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 200));
    try {
      const resp = await fetch('http://localhost:9224/json');
      const list = await resp.json();
      const page = list.find(t => t.type === 'page' && t.url.includes('localhost:8082'));
      if (page && page.webSocketDebuggerUrl) {
        targetWsUrl = page.webSocketDebuggerUrl;
        break;
      }
    } catch (e) {}
  }

  if (!targetWsUrl) {
    chromeProc.kill();
    server.close();
    process.exit(1);
  }

  const ws = new WebSocket(targetWsUrl);
  let msgId = 1;
  const pending = new Map();

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  };

  function sendCDP(method, params = {}) {
    return new Promise((resolve) => {
      const id = msgId++;
      pending.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  ws.onopen = async () => {
    await new Promise(r => setTimeout(r, 1000));

    // Clear any previous localStorage before starting fresh test
    await sendCDP('Runtime.evaluate', { expression: 'localStorage.clear()' });
    await sendCDP('Page.navigate', { url: 'http://localhost:8082/index.html' });
    await new Promise(r => setTimeout(r, 1000));

    console.log('--- TEST 1: Verify all alerts default to OFF ---');
    // Click sample test screen
    await sendCDP('Runtime.evaluate', { expression: 'document.getElementById("btnSampleTest").click()' });
    await new Promise(r => setTimeout(r, 1000));

    // Check EXP values
    const expNum = await sendCDP('Runtime.evaluate', { expression: 'document.getElementById("expHeroNum").textContent' });
    console.log('EXP Hero:', expNum.result.result.value);

    // Verify NO alerts are active by default
    const isAlertDefault = await sendCDP('Runtime.evaluate', {
      expression: 'document.body.classList.contains("red-alert-active")'
    });
    const alertingCellsCount = await sendCDP('Runtime.evaluate', {
      expression: 'document.querySelectorAll(".hotbar-cell.alerting").length'
    });
    console.log('Default Red Alert Active:', isAlertDefault.result.result.value);
    console.log('Default Alerting Cells Count:', alertingCellsCount.result.result.value);

    if (isAlertDefault.result.result.value !== false || alertingCellsCount.result.result.value !== 0) {
      console.error('FAILED: Expected all alerts to be OFF by default!');
      process.exit(1);
    }
    console.log('✓ TEST 1 PASSED: All alerts defaulted to OFF.');

    console.log('\n--- TEST 2: Modify inputs & verify saved to localStorage ---');
    // 1. Switch to Hotbar tab
    await sendCDP('Runtime.evaluate', { expression: 'document.querySelector("[data-tab=\'hotbar\']").click()' });
    await new Promise(r => setTimeout(r, 200));

    // 2. Select Shift cell (child 5), change threshold to 75, and enable alert
    await sendCDP('Runtime.evaluate', {
      expression: `
        document.querySelector(".hotbar-cell:nth-child(5)").click();
        const input = document.getElementById("configThresholdInput");
        input.value = 75;
        input.dispatchEvent(new Event('change'));
        const enableCb = document.getElementById("configCellEnable");
        enableCb.checked = true;
        enableCb.dispatchEvent(new Event('change'));
      `
    });

    // 3. Select Del cell (child 10 = row 2, col 1)
    await sendCDP('Runtime.evaluate', {
      expression: 'document.querySelector(".hotbar-cell:nth-child(10)").click()'
    });

    // 4. Select rolling window 10m
    await sendCDP('Runtime.evaluate', {
      expression: 'document.querySelector(".pill-btn[data-window=\'10m\']").click()'
    });

    // 5. Toggle mute
    await sendCDP('Runtime.evaluate', {
      expression: 'document.getElementById("btnMute").click()'
    });

    // Check localStorage content directly in browser
    const storedAlerts = await sendCDP('Runtime.evaluate', {
      expression: 'localStorage.getItem("maple_exp_cell_alerts")'
    });
    const storedCell = await sendCDP('Runtime.evaluate', {
      expression: 'localStorage.getItem("maple_exp_selected_cell")'
    });
    const storedWindow = await sendCDP('Runtime.evaluate', {
      expression: 'localStorage.getItem("maple_exp_selected_window")'
    });
    const storedMute = await sendCDP('Runtime.evaluate', {
      expression: 'localStorage.getItem("maple_exp_is_muted")'
    });

    console.log('Stored Selected Cell:', storedCell.result.result.value);
    console.log('Stored Selected Window:', storedWindow.result.result.value);
    console.log('Stored Mute State:', storedMute.result.result.value);

    const parsedAlerts = JSON.parse(storedAlerts.result.result.value);
    console.log('Stored Shift [1,0] Config:', parsedAlerts['1,0']);

    if (
      parsedAlerts['1,0'].threshold !== 75 ||
      parsedAlerts['1,0'].enabled !== true ||
      storedCell.result.result.value !== '[2,1]' ||
      storedWindow.result.result.value !== '10m' ||
      storedMute.result.result.value !== 'true'
    ) {
      console.error('FAILED: Stored inputs mismatch!');
      process.exit(1);
    }
    console.log('✓ TEST 2 PASSED: Inputs properly serialized to localStorage.');

    console.log('\n--- TEST 3: Reload page & verify inputs restored from localStorage ---');
    await sendCDP('Page.navigate', { url: 'http://localhost:8082/index.html' });
    await new Promise(r => setTimeout(r, 1200));

    // Verify restored window pill
    const activeWindowPill = await sendCDP('Runtime.evaluate', {
      expression: 'document.querySelector(".pill-btn.active").dataset.window'
    });
    console.log('Restored Active Window Pill:', activeWindowPill.result.result.value);

    // Verify restored mute button text
    const muteBtnText = await sendCDP('Runtime.evaluate', {
      expression: 'document.getElementById("btnMute").textContent.trim()'
    });
    console.log('Restored Mute Button Text:', muteBtnText.result.result.value);

    // Switch to Hotbar tab and inspect Del cell (child 10) selection and Shift config
    await sendCDP('Runtime.evaluate', { expression: 'document.querySelector("[data-tab=\'hotbar\']").click()' });
    await new Promise(r => setTimeout(r, 200));

    const selectedCellName = await sendCDP('Runtime.evaluate', {
      expression: 'document.getElementById("configCellName").textContent'
    });
    console.log('Restored Selected Cell Name:', selectedCellName.result.result.value);

    // Now click Shift cell to verify its saved threshold (75) and enabled (true)
    await sendCDP('Runtime.evaluate', {
      expression: 'document.querySelector(".hotbar-cell:nth-child(5)").click()'
    });
    const shiftRestoredThresh = await sendCDP('Runtime.evaluate', {
      expression: 'document.getElementById("configThresholdInput").value'
    });
    const shiftRestoredEnable = await sendCDP('Runtime.evaluate', {
      expression: 'document.getElementById("configCellEnable").checked'
    });
    console.log('Restored Shift Threshold:', shiftRestoredThresh.result.result.value);
    console.log('Restored Shift Enabled:', shiftRestoredEnable.result.result.value);

    const test3Pass = (
      activeWindowPill.result.result.value === '10m' &&
      muteBtnText.result.result.value === '🔇 Unmute' &&
      selectedCellName.result.result.value === 'Slot [Del] Config' &&
      shiftRestoredThresh.result.result.value === '75' &&
      shiftRestoredEnable.result.result.value === true
    );

    console.log('================================================================');
    if (test3Pass) {
      console.log('>>> ALL TESTS PASSED: DEFAULTS OFF & LOCALSTORAGE RESTORATION VERIFIED! <<<');
    } else {
      console.error('FAILED: Restored values did not match!');
    }
    console.log('================================================================');

    ws.close();
    chromeProc.kill();
    server.close();
    process.exit(test3Pass ? 0 : 1);
  };
});

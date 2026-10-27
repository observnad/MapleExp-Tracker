const { spawnSync } = require('child_process');
const path = require('path');
const assert = require('assert');

const { CVEngine } = require('../js/cv-engine.js');
const { RAW_TEMPLATES } = require('../js/templates.js');
const { ExpDetector } = require('../js/detector.js');
const { HotbarDetector } = require('../js/hotbar.js');

console.log('--- Running JS Detector & Hotbar Unit Tests ---');

// Helper to convert raw JSON {width, height, data} into ImageData-like object
function makeImageData(raw) {
  const { width, height, data } = raw;
  let rgba;
  if (data.length === width * height * 4) {
    rgba = new Uint8ClampedArray(data);
  } else {
    rgba = new Uint8ClampedArray(width * height * 4);
    let p = 0;
    for (let i = 0; i < data.length; i += 3) {
      rgba[p++] = data[i];
      rgba[p++] = data[i + 1];
      rgba[p++] = data[i + 2];
      rgba[p++] = 255;
    }
  }
  return { width, height, data: rgba };
}

function loadSampleImage(filename) {
  const pyScript = path.join(__dirname, 'load_sample.py');
  const pyExe = path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe');
  const res = spawnSync(pyExe, [pyScript, filename], { maxBuffer: 30 * 1024 * 1024 });
  if (res.status !== 0) {
    throw new Error('Failed to load sample image: ' + filename);
  }
  return makeImageData(JSON.parse(res.stdout.toString()));
}

const expLogoTmpl = makeImageData(RAW_TEMPLATES.exp_logo);
const frameBottomTmpl = makeImageData(RAW_TEMPLATES.frame_bottom);
const ctrlBtnTmpl = makeImageData(RAW_TEMPLATES.ctrl_btn);

// Test 1: bottom_bar.png (1920x120)
{
  const roiData = loadSampleImage('bottom_bar.png');
  const engine = new CVEngine();
  const det = new ExpDetector(engine, expLogoTmpl);

  det.isLocked = true;
  det.lockedLoc = { x: 997, y: 65 };
  det.lockedScale = 1.0;
  det.lockedClientSize = { w: 1920, h: 120 };

  const res = det.detect(roiData, 1920, 120);
  console.log('bottom_bar EXP detection result:', res.success, res.exp_value, res.exp_pct, res.raw_text, 'bar_pct:', res.bar_pct);

  assert.strictEqual(res.success, true);
  assert.strictEqual(res.exp_value, 10869);
  assert.strictEqual(res.exp_pct, 37.51);
  console.log('✓ bottom_bar EXP OCR and bar validation passed');
}

// Test 2: exp_twenty_pct.png (1922x311)
{
  const roiData = loadSampleImage('exp_twenty_pct.png');
  const engine = new CVEngine();
  const det = new ExpDetector(engine, expLogoTmpl);

  det.isLocked = true;
  det.lockedLoc = { x: 998, y: 277 };
  det.lockedScale = 1.0;
  det.lockedClientSize = { w: 1922, h: 311 };

  const res = det.detect(roiData, 1922, 311);
  console.log('exp_twenty_pct EXP detection result:', res.success, res.exp_value, res.exp_pct, res.raw_text, 'bar_pct:', res.bar_pct);

  assert.strictEqual(res.success, true);
  assert.strictEqual(res.exp_value, 13308);
  assert.strictEqual(res.exp_pct, 20.90);
  console.log('✓ exp_twenty_pct EXP OCR passed (13,308 [20.90%])');

  // Test Hotbar detection on exp_twenty_pct
  const hb = new HotbarDetector(engine, frameBottomTmpl, ctrlBtnTmpl);
  hb.isLocked = true;
  hb.lockedLoc = { x: 1213, y: 132 };
  hb.lockedScale = 1.0;

  const hres = hb.detect(roiData, 1.0);
  console.log('exp_twenty_pct Hotbar detection result:', hres.success, 'confidence:', hres.confidence);
  console.log('Quantities:', hres.quantities);

  assert.strictEqual(hres.success, true);
  assert.strictEqual(hres.quantities['1,0'], 36);
  assert.strictEqual(hres.quantities['1,1'], 20);
  assert.strictEqual(hres.quantities['1,2'], 44);
  assert.strictEqual(hres.quantities['1,3'], 0);
  assert.strictEqual(hres.quantities['2,1'], 47);
  console.log('✓ exp_twenty_pct Hotbar quantities verified exactly: Shift=36, Ins=20, Hm=44, Pup=0, Del=47');
}

console.log('>>> ALL JS DETECTOR & HOTBAR TESTS PASSED 100%! <<<');

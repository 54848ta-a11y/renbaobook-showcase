// -*- coding: utf-8 -*-
const fs = require('fs');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync('index.html', 'utf-8');
const errors = [];

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  resources: 'usable',
  url: 'https://example.com/',
  beforeParse(window) {
    window.localStorage = {
      _d: {},
      getItem(k){ return this._d[k] ?? null; },
      setItem(k,v){ this._d[k]=String(v); },
      removeItem(k){ delete this._d[k]; },
    };
    window.addEventListener('error', e => errors.push('window error: ' + e.message));
  }
});

// 等待脚本执行
setTimeout(() => {
  const doc = dom.window.document;
  const cards = doc.querySelectorAll('#grid .card');
  const dv = doc.querySelectorAll('#grid .card .cover .dv');
  const dupTitle = doc.querySelectorAll('#grid .card .cbody .t');
  const borrowed = doc.querySelectorAll('#grid .card .borrowed');
  const count = doc.querySelector('#count') ? doc.querySelector('#count').textContent : '(none)';
  const cats = doc.querySelectorAll('#cats .cat').length;
  const total = doc.querySelector('#stTotal') ? doc.querySelector('#stTotal').textContent : '(none)';

  // 首页首屏应跨多个类目（不再是清一色哲学 B）
  const catSet = new Set([...cards].map(c => c.querySelector('.tag') ? c.querySelector('.tag').textContent.trim() : ''));

  // 前 10 张（前 5 行，移动端 2 列）应至少有一本已借出
  const first10 = [...cards].slice(0, 10);
  const borrowedInFirst10 = first10.filter(c => c.querySelector('.borrowed')).length;
  const placeholder = doc.querySelector('#q') ? doc.querySelector('#q').getAttribute('placeholder') : '';

  console.log('--- SMOKE TEST ---');
  console.log('grid cards (first page):', cards.length);
  console.log('.dv dividers in cards:', dv.length);
  console.log('duplicate body titles (.cbody .t):', dupTitle.length);
  console.log('borrowed badges on first page:', borrowed.length);
  console.log('category chips:', cats);
  console.log('stTotal:', total);
  console.log('count text:', count);
  console.log('distinct call-number tags on first page:', catSet.size);
  console.log('borrowed in first 10 cards:', borrowedInFirst10);
  console.log('search placeholder:', placeholder);
  console.log('JS errors:', errors.length ? errors : 'none');

  // 模拟「加载更多」：点击后卡片数翻倍且无重复 id
  let pagOk = true, dupIds = 0;
  const moreBtn = doc.querySelector('#moreBtn');
  if (moreBtn) {
    moreBtn.click();
    const after = doc.querySelectorAll('#grid .card');
    const ids = [...after].map(c => c.dataset.id);
    dupIds = ids.length - new Set(ids).size;
    pagOk = after.length === 120 && dupIds === 0;
    console.log('after load-more cards:', after.length, 'duplicate ids:', dupIds);
  }

  // 校验：每张卡都有 .dv 分隔线
  const cardsWithoutDv = cards.length - dv.length;
  console.log('cards missing .dv:', cardsWithoutDv);

  if (cards.length === 0) { console.log('FAIL: no cards rendered'); process.exit(1); }
  if (dv.length !== cards.length) { console.log('FAIL: .dv not on every card'); process.exit(1); }
  if (dupTitle.length !== 0) { console.log('FAIL: duplicate body title still present'); process.exit(1); }
  if (catSet.size < 5) { console.log('FAIL: first page dominated by single category (', catSet.size, 'distinct)'); process.exit(1); }
  if (borrowedInFirst10 < 1) { console.log('FAIL: no borrowed book in first 10 cards'); process.exit(1); }
  if (!placeholder || !placeholder.includes('模糊查找')) { console.log('FAIL: search placeholder not updated'); process.exit(1); }
  if (!pagOk) { console.log('FAIL: load-more pagination broken'); process.exit(1); }
  if (cats < 10) { console.log('FAIL: categories not rendered'); process.exit(1); }
  if (errors.length) { console.log('FAIL: JS errors present'); process.exit(1); }
  console.log('PASS');
  process.exit(0);
}, 1500);

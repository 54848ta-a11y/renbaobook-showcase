// -*- coding: utf-8 -*-
// 验证：搜索相关性排序 + 清除按钮显隐
const fs = require('fs');
const { JSDOM } = require('jsdom');
const html = fs.readFileSync('index.html', 'utf-8');
const errors = [];
const dom = new JSDOM(html, {
  runScripts: 'dangerously', resources: 'usable', url: 'https://example.com/',
  beforeParse(w){ w.addEventListener('error', e=>errors.push(e.message)); }
});
const doc = dom.window.document;

setTimeout(() => {
  const q = doc.querySelector('#q');
  const clear = doc.querySelector('#qClear');

  // 注入搜索词（绕过 debounce 直接触发 input）
  q.value = '经济';
  q.dispatchEvent(new dom.window.Event('input', { bubbles: true }));

  setTimeout(() => {
    const cards = [...doc.querySelectorAll('#grid .card')];
    const titles = cards.map(c => c.querySelector('.cover .ct').textContent);
    const clearVisible = clear.style.display !== 'none';
    const count = doc.querySelector('#count').textContent;

    // 相关性：标题直接含“经济”的应排在前（标题前缀/包含权重高于出版社）
    const topHasTitle = titles[0].includes('经济');

    console.log('--- SEARCH SMOKE ---');
    console.log('result count:', cards.length);
    console.log('count text:', count);
    console.log('clear button visible after typing:', clearVisible);
    console.log('top result title:', titles[0]);
    console.log('top result title contains 经济:', topHasTitle);
    console.log('JS errors:', errors.length ? errors : 'none');

    // 清除测试
    clear.click();
    setTimeout(() => {
      const afterClear = doc.querySelector('#grid .card');
      const clearHidden = clear.style.display === 'none';
      console.log('after clear: clear hidden =', clearHidden, '| first card exists =', !!afterClear);
      const ok = cards.length > 0 && clearVisible && topHasTitle && clearHidden && !!afterClear && errors.length === 0;
      console.log(ok ? 'PASS' : 'FAIL');
      process.exit(ok ? 0 : 1);
    }, 400);
  }, 400);
}, 1200);

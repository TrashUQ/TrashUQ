const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const filePath = `file://${path.resolve(__dirname, 'index.html')}`;
  
  console.log(`Loading ${filePath}...`);
  await page.goto(filePath, { waitUntil: 'networkidle' });
  
  // Wait for animations and charts to render
  console.log('Waiting for charts and diagrams to render...');
  await page.waitForTimeout(5000); 
  
  console.log('Exporting PDF...');
  await page.pdf({
    path: 'TrashUQ_presentation.pdf',
    format: 'Letter',
    landscape: true,
    printBackground: true,
    margin: { top: '0px', right: '0px', bottom: '0px', left: '0px' }
  });

  await browser.close();
  console.log('PDF exported successfully!');
})();

const fs = require('fs');
const path = require('path');

const cssPath = path.join(__dirname, '..', 'web-client', 'static', 'css', 'unocss.css');

const banner = `/* build timestamp: ${new Date().toISOString()} */\n`;

let css = fs.readFileSync(cssPath, 'utf8');
if (css.startsWith('/* build timestamp:')) {
  css = css.replace(/^\/\* build timestamp:.*?\*\/\n/, banner);
} else {
  css = banner + css;
}
fs.writeFileSync(cssPath, css);


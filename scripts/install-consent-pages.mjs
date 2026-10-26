import fs from 'node:fs';
import path from 'node:path';

const dirs = ['de','en','es','fr','it','pl'];
const files = ['index.html'];
for (const dir of dirs) {
  const search = (folder) => {
    for (const entry of fs.readdirSync(folder, { withFileTypes:true })) {
      const name = path.join(folder,entry.name);
      if (entry.isDirectory()) search(name);
      else if (entry.isFile() && entry.name === 'index.html') files.push(name);
    }
  };
  search(dir);
}
if (files.length !== 41) throw new Error('Expected 41 public index.html pages, got '+files.length);
const src = '<script src="/bfl-knowledge-consent.js" defer></script>';
const unguarded = 'window.dataLayer.push(payload);';
const gated = "if (window.BioFarmLabConsent?.getAnalyticsConsent?.() === 'granted') window.dataLayer.push(payload);";
for (const file of files) {
  let s = fs.readFileSync(file,'utf8');
  if (!s.includes('</head>')) throw new Error('Missing HEAD in '+file);
  if (!s.includes(src)) s = s.replace('</head>',src+'</head>');
  if (!s.includes(gated)) {
    if (!s.includes(unguarded)) throw new Error('Tracking event not found in '+file);
    s = s.replace(unguarded,gated);
  }
  if (s.split(src).length !== 2) throw new Error('Duplicate consent tag in '+file);
  fs.writeFileSync(file,s);
}
console.log('Updated exactly '+files.length+' pages; all commercial events consent-gated.');

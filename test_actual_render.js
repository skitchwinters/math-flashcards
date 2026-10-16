const fs = require('fs');

// Load KaTeX
const katexCode = fs.readFileSync('katex.min.js', 'utf8');
const katexModule = { exports: {} };
new Function('module', 'exports', katexCode)(katexModule, katexModule.exports);
const katex = katexModule.exports;

const KATEX_MACROS = {
  "\\C": "\\mathbb{C}",
  "\\R": "\\mathbb{R}",
  "\\N": "\\mathbb{N}",
  "\\Z": "\\mathbb{Z}",
  "\\Q": "\\mathbb{Q}",
  "\\id": "\\operatorname{id}",
  "\\mod": "\\ (\\operatorname{mod} #1)",
  "\\cyc": "\\langle #1 \\rangle",
  "\\ip": "\\langle #1 \\rangle",
  "\\intr": "\\operatorname{int}",
  "\\dom": "\\operatorname{dom}",
  "\\inc": "\\text{\\footnotesize\\phantom{.}I\\phantom{.}}",
  "\\rbracket": "]",
  "\\abs": "\\left|#1\\right|",
  "\\norm": "\\left\\|#1\\right\\|",
  "\\slash": "/",
  "\\emph": "\\textcolor{red}{#1}"
};

const data = JSON.parse(fs.readFileSync('definitions.json', 'utf8'));

// Find card for infinite union in MATH 301
let found = false;
data.courses.forEach(c => {
  if (c.code === 'MATH 301') {
    c.cards.forEach(card => {
      if (card.term.includes('bigcup') || card.term.includes('infty') || card.definition.includes('bigcup')) {
        console.log('=== CARD FOUND ===');
        console.log('TERM:', card.term);
        console.log('DEFINITION:', card.definition);
        
        // Extract display math
        const dm = card.definition.match(/\\\[(.*?)\\\]/s);
        if (dm) {
          const tex = dm[1].trim();
          console.log('\n--- EXTRACTED TEX ---');
          console.log(tex);
          try {
            const html = katex.renderToString(tex, {
              displayMode: true,
              macros: KATEX_MACROS,
              throwOnError: true
            });
            console.log('\n--- RENDERED HTML RESULT ---');
            console.log(html.slice(0, 150) + '... (' + html.length + ' chars)');
          } catch (e) {
            console.error('\n--- RENDER FAILED ---');
            console.error(e.message);
          }
        }
      }
    });
  }
});

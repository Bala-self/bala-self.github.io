// Tiny, early theme initialization prevents a light/dark flash. No network or analytics.
'use strict';
(()=>{let theme='system';try{theme=JSON.parse(localStorage.getItem('pocket-theme'))||'system';}catch{}
const system=matchMedia('(prefers-color-scheme: dark)');
function apply(){const dark=theme==='dark'||(theme==='system'&&system.matches);document.documentElement.dataset.theme=dark?'dark':'light';const button=document.getElementById('theme');if(button)button.setAttribute('aria-label',`Switch to ${dark?'light':'dark'} theme`);const meta=document.querySelector('meta[name="theme-color"]');if(meta)meta.content=dark?'#15201b':'#f8f9f5';}
apply();system.addEventListener('change',apply);document.addEventListener('DOMContentLoaded',()=>{apply();document.getElementById('theme')?.addEventListener('click',()=>{theme=document.documentElement.dataset.theme==='dark'?'light':'dark';try{localStorage.setItem('pocket-theme',JSON.stringify(theme));}catch{}apply();});});})();

// Study 3 Chatbot — Qualtrics-side runtime.
// Renders the chat interface, dispatches stage calls (elicit / generate /
// recommend) to the worker, and persists session state to Qualtrics
// embedded data.
//
// "Recommended" carousel badge is condition-aware:
//   biased  → badge on focal product (data.recommended_index)
//   honest  → badge on spec-dominant product (data.spec_dominant_index)
//   neutral → no badge
//
// Spec format accepts both {key:"display"} and {key:{display,value}}. Every
// /chat call ships session_id, condition, ai_brand, category, turn_number,
// prolific_pid. Every turn writes msg_N_ts / response_N_ts (per-turn
// timestamps) to embedded data.
Qualtrics.SurveyEngine.addOnload(function(){});
Qualtrics.SurveyEngine.addOnReady(function(){
  var self = this;
  var URL = 'https://study3-chatbot.webmarinelli.workers.dev/chat';
  var SID = 'S3_' + Date.now() + '_' + Math.random().toString(36).slice(2,8);
  var history = [], userTurns = 0, turnN = 0, stage = 'elicit';
  var msgN = 0, responseN = 0; // independent counters so msg_N pairs with response_N (not response_N+1)
  var assortment = null, s3sys = '', searchTimer = null, noAutoScroll = false;
  var confirmed = false; // Gate: only true after user clicks Confirm
  var selectedProduct = null; // Set only when card click resolves to a product in assortment.products; Confirm requires this

  // Participant identifiers for log correlation (optional; null if not set)
  var PROLIFIC_PID = null;
  try { PROLIFIC_PID = Qualtrics.SurveyEngine.getEmbeddedData('PROLIFIC_PID') || null; } catch(e){}

  Qualtrics.SurveyEngine.setEmbeddedData('study3_session_id', SID);
  Qualtrics.SurveyEngine.setEmbeddedData('study3_session_start_ts', new Date().toISOString());

  // ── Hard-gate the Next button until Confirm is clicked ──────
  // CSS-only approach: a single <style> block with !important rules hides Next/Previous.
  // The observer RE-APPENDS the <style> block if Qualtrics rips it out — it does NOT
  // set inline styles on the button itself (inline styles would persist past teardown
  // and leave the button stuck hidden, causing the "arrow does nothing" lockup).
  self.hideNextButton();
  var s3GateStyle = document.createElement('style');
  s3GateStyle.id = 's3-gate-style';
  s3GateStyle.textContent =
    '#NextButton,#Buttons input[id="NextButton"],input[id="NextButton"]{display:none !important;visibility:hidden !important;pointer-events:none !important;}' +
    '#PreviousButton{display:none !important;}';
  document.head.appendChild(s3GateStyle);
  // Observer only ensures the <style> element stays in the DOM. No inline styles written.
  var s3GateObserver = new MutationObserver(function(){
    if (confirmed) return;
    if (!document.getElementById('s3-gate-style')) {
      document.head.appendChild(s3GateStyle);
    }
  });
  try { s3GateObserver.observe(document.head, {childList:true}); } catch(e){}
  var s3KeyBlocker = function(e){
    if (confirmed) return;
    if (e.key === 'Enter' || e.keyCode === 13) {
      var inp = document.getElementById('s3-input');
      if (document.activeElement !== inp) { e.preventDefault(); e.stopPropagation(); }
    }
  };
  document.addEventListener('keydown', s3KeyBlocker, true);
  // Retry in case Qualtrics re-renders the button after our initial hide.
  setTimeout(function(){ if(!confirmed) self.hideNextButton(); }, 500);
  setTimeout(function(){ if(!confirmed) self.hideNextButton(); }, 2000);
  setTimeout(function(){ if(!confirmed) self.hideNextButton(); }, 5000);
  // Telemetry: flag any attempt to advance without confirming (should be impossible with the gate above).
  Qualtrics.SurveyEngine.addOnPageSubmit(function(type){
    try {
      if (type === 'next' && !confirmed) {
        Qualtrics.SurveyEngine.setEmbeddedData('study3_bypass_attempt','true');
      }
    } catch(e){}
  });

  // Read condition (biased/honest/neutral) from embedded data
  var condition = 'biased'; // default
  try { condition = Qualtrics.SurveyEngine.getEmbeddedData('study3_condition') || 'biased'; } catch(e){}

  // ── Brand Skins ─────────────────────────────────────────────
  // Placeholder SVGs — will be replaced with real logos
  var SKINS = {
    chatgpt: {
      name:'ChatGPT Shopping', chatBg:'#FFFFFF', aiBg:'transparent', userBg:'#f4f4f4', userText:'#1a1a1a',
      text:'#1a1a1a', sendBg:'#000000', accent:'#000000', headerBg:'#FFFFFF', headerBorder:'#E5E5E5',
      showAvatar:false, inputPlaceholder:'Ask anything', btnColor:'#444',
      svg:'<svg width="24" height="24" fill="#10A37F" viewBox="0 0 16 16"><path d="M14.949 6.547a3.94 3.94 0 0 0-.348-3.273 4.11 4.11 0 0 0-4.4-1.934A4.1 4.1 0 0 0 8.423.2 4.15 4.15 0 0 0 6.305.086a4.1 4.1 0 0 0-1.891.948 4.04 4.04 0 0 0-1.158 1.753 4.1 4.1 0 0 0-1.563.679A4 4 0 0 0 .554 4.72a3.99 3.99 0 0 0 .502 4.731 3.94 3.94 0 0 0 .346 3.274 4.11 4.11 0 0 0 4.402 1.933c.382.425.852.764 1.377.995.526.231 1.095.35 1.67.346 1.78.002 3.358-1.132 3.901-2.804a4.1 4.1 0 0 0 1.563-.68 4 4 0 0 0 1.14-1.253 3.99 3.99 0 0 0-.506-4.716m-6.097 8.406a3.05 3.05 0 0 1-1.945-.694l.096-.054 3.23-1.838a.53.53 0 0 0 .265-.455v-4.49l1.366.778q.02.011.025.035v3.722c-.003 1.653-1.361 2.992-3.037 2.996m-6.53-2.75a2.95 2.95 0 0 1-.36-2.01l.095.057L5.29 12.09a.53.53 0 0 0 .527 0l3.949-2.246v1.555a.05.05 0 0 1-.022.041L6.473 13.3c-1.454.826-3.311.335-4.15-1.098m-.85-6.94A3.02 3.02 0 0 1 3.07 3.949v3.785a.51.51 0 0 0 .262.451l3.93 2.237-1.366.779a.05.05 0 0 1-.048 0L2.585 9.342a2.98 2.98 0 0 1-1.113-4.094zm11.216 2.571L8.747 5.576l1.362-.776a.05.05 0 0 1 .048 0l3.265 1.86a3 3 0 0 1 1.173 1.207 2.96 2.96 0 0 1-.27 3.2 3.05 3.05 0 0 1-1.36.997V8.279a.52.52 0 0 0-.276-.445m1.36-2.015-.097-.057-3.226-1.855a.53.53 0 0 0-.53 0L6.249 6.153V4.598a.04.04 0 0 1 .019-.04L9.533 2.7a3.07 3.07 0 0 1 3.257.139c.474.325.843.778 1.066 1.303.223.526.289 1.103.191 1.664zM5.503 8.575 4.139 7.8a.05.05 0 0 1-.026-.037V4.049c0-.57.166-1.127.476-1.607s.752-.864 1.275-1.105a3.08 3.08 0 0 1 3.234.41l-.096.054-3.23 1.838a.53.53 0 0 0-.265.455zm.742-1.577 1.758-1 1.762 1v2l-1.755 1-1.762-1z"/></svg>'
    },
    claude: {
      name:'Claude Shopping', chatBg:'#FAF9F5', aiBg:'transparent', userBg:'#f5f0e8', userText:'#141413',
      text:'#141413', sendBg:'#353535', accent:'#DA7756', headerBg:'#FAF9F5', headerBorder:'#E8E6DC',
      showAvatar:true, inputPlaceholder:'Reply...', btnColor:'#DA7756',
      svg:'<svg width="24" height="24" fill="#DA7756" viewBox="0 0 16 16"><path d="m3.127 10.604 3.135-1.76.053-.153-.053-.085H6.11l-.525-.032-1.791-.048-1.554-.065-1.505-.08-.38-.081L0 7.832l.036-.234.32-.214.455.04 1.009.069 1.513.105 1.097.064 1.626.17h.259l.036-.105-.089-.065-.068-.064-1.566-1.062-1.695-1.121-.887-.646-.48-.327-.243-.306-.104-.67.435-.48.585.04.15.04.593.456 1.267.981 1.654 1.218.242.202.097-.068.012-.049-.109-.181-.9-1.626-.96-1.655-.428-.686-.113-.411a2 2 0 0 1-.068-.484l.496-.674L4.446 0l.662.089.279.242.411.94.666 1.48 1.033 2.014.302.597.162.553.06.17h.105v-.097l.085-1.134.157-1.392.154-1.792.052-.504.25-.605.497-.327.387.186.319.456-.045.294-.19 1.23-.37 1.93-.243 1.29h.142l.161-.16.654-.868 1.097-1.372.484-.545.565-.601.363-.287h.686l.505.751-.226.775-.707.895-.585.759-.839 1.13-.524.904.048.072.125-.012 1.897-.403 1.024-.186 1.223-.21.553.258.06.263-.218.536-1.307.323-1.533.307-2.284.54-.028.02.032.04 1.029.098.44.024h1.077l2.005.15.525.346.315.424-.053.323-.807.411-3.631-.863-.872-.218h-.12v.073l.726.71 1.331 1.202 1.667 1.55.084.383-.214.302-.226-.032-1.464-1.101-.565-.497-1.28-1.077h-.084v.113l.295.432 1.557 2.34.08.718-.112.234-.404.141-.444-.08-.911-1.28-.94-1.44-.759-1.291-.093.053-.448 4.821-.21.246-.484.186-.403-.307-.214-.496.214-.98.258-1.28.21-1.016.19-1.263.112-.42-.008-.028-.092.012-.953 1.307-1.448 1.957-1.146 1.227-.274.109-.477-.247.045-.44.266-.39 1.586-2.018.956-1.25.617-.723-.004-.105h-.036l-4.212 2.736-.75.096-.324-.302.04-.496.154-.162 1.267-.871z"/></svg>'
    },
    gemini: {
      name:'Gemini Shopping', chatBg:'#FFFFFF', aiBg:'transparent', userBg:'#D3E3FD', userText:'#1F1F1F',
      text:'#1F1F1F', sendBg:'#4285f4', accent:'#4285f4', headerBg:'#FFFFFF', headerBorder:'#E0E0E0',
      showAvatar:true, inputPlaceholder:'Ask Gemini', btnColor:'#4285f4',
      svg:'<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="gg" x1="6.8" y1="16" x2="19.2" y2="5.5" gradientUnits="userSpaceOnUse"><stop stop-color="#4893FC"/><stop offset=".77" stop-color="#969DFF"/><stop offset="1" stop-color="#BD99FE"/></linearGradient></defs><path d="M12 0c.25 0 .47.17.53.41a14.3 14.3 0 0 0 .74 2.18c.79 1.84 1.88 3.45 3.26 4.83 1.38 1.38 2.99 2.47 4.83 3.26.7.3 1.43.55 2.18.74.24.06.41.28.41.53s-.17.47-.41.53a14.3 14.3 0 0 0-2.18.74c-1.84.79-3.45 1.88-4.83 3.26-1.38 1.38-2.47 2.99-3.26 4.83-.3.7-.55 1.43-.74 2.18a.55.55 0 0 1-.53.41c-.25 0-.47-.17-.53-.41a14.3 14.3 0 0 0-.74-2.18c-.79-1.84-1.88-3.45-3.26-4.83-1.38-1.38-2.99-2.47-4.83-3.26a14.3 14.3 0 0 0-2.18-.74A.55.55 0 0 1 0 11.95c0-.25.17-.47.41-.53a14.3 14.3 0 0 0 2.18-.74c1.84-.79 3.45-1.88 4.83-3.26 1.38-1.38 2.47-2.99 3.26-4.83.3-.7.55-1.43.74-2.18A.55.55 0 0 1 12 0z" fill="url(#gg)"/></svg>'
    },
    perplexity: {
      name:'Perplexity Shopping', chatBg:'#FFFFFF', aiBg:'transparent', userBg:'#F0F0F0', userText:'#1A1A1A',
      text:'#1A1A1A', sendBg:'#1FB8CD', accent:'#1FB8CD', headerBg:'#FFFFFF', headerBorder:'#E8E8E8',
      showAvatar:false, inputPlaceholder:'Ask a follow-up', btnColor:'#1FB8CD',
      svg:'<svg width="24" height="24" fill="#1FB8CD" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 .188a.5.5 0 0 1 .503.5V4.03l3.022-2.92.059-.048a.51.51 0 0 1 .49-.054.5.5 0 0 1 .306.46v3.247h1.117l.1.01a.5.5 0 0 1 .403.49v5.558a.5.5 0 0 1-.503.5H12.38v3.258a.5.5 0 0 1-.312.462.51.51 0 0 1-.55-.11l-3.016-3.018v3.448c0 .275-.225.5-.503.5a.5.5 0 0 1-.503-.5v-3.448l-3.018 3.019a.51.51 0 0 1-.548.11.5.5 0 0 1-.312-.463v-3.258H2.503a.5.5 0 0 1-.503-.5V5.215l.01-.1c.047-.229.25-.4.493-.4H3.62V1.469l.006-.074a.5.5 0 0 1 .302-.387.51.51 0 0 1 .547.102l3.023 2.92V.687c0-.276.225-.5.503-.5M4.626 9.333v3.984l2.87-2.872v-4.01zm3.877 1.113 2.871 2.871V9.333l-2.87-2.897zm3.733-1.668a.5.5 0 0 1 .145.35v1.145h.612V5.715H9.201zm-9.23 1.495h.613V9.13c0-.131.052-.257.145-.35l3.033-3.064h-3.79zm1.62-5.558H6.76L4.626 2.652zm4.613 0h2.134V2.652z"/></svg>'
    }
  };

  // Pick random brand (or read from embedded data)
  var brandKey = null;
  try { brandKey = Qualtrics.SurveyEngine.getEmbeddedData('study3_ai_brand'); } catch(e){}
  if (!brandKey || !SKINS[brandKey]) {
    var keys = Object.keys(SKINS);
    brandKey = keys[Math.floor(Math.random() * keys.length)];
  }
  var skin = SKINS[brandKey];
  ed('study3_ai_brand', brandKey);

  // Apply skin to DOM
  var chatEl = document.getElementById('s3-chat');
  if (chatEl) chatEl.style.background = skin.chatBg;
  var hdr = document.getElementById('s3-header');
  if (hdr) { hdr.style.background = skin.headerBg; hdr.style.borderBottomColor = skin.headerBorder; }
  var lbl = document.getElementById('s3-brand-label');
  if (lbl) { lbl.textContent = skin.name; lbl.style.color = skin.text; }
  var av = document.getElementById('s3-brand-avatar');
  if (av) av.innerHTML = skin.svg;
  var snd = document.getElementById('s3-send');
  if (snd) { snd.style.background = skin.sendBg; }
  var inp0 = document.getElementById('s3-input');
  if (inp0) {
    inp0.placeholder = skin.inputPlaceholder || 'What are you looking for?';
    inp0.addEventListener('focus', function(){ this.style.borderColor = skin.accent; });
    inp0.addEventListener('blur', function(){ this.style.borderColor = '#ddd'; });
    // Send button activates when there's text
    inp0.addEventListener('input', function(){
      var snd = document.getElementById('s3-send');
      if(snd){
        if(this.value.trim()){
          snd.style.background = skin.sendBg;
          snd.style.opacity = '1';
        } else {
          snd.style.opacity = '0.35';
        }
      }
    });
  }
  // Start send button muted
  if(snd) snd.style.opacity = '0.35';
  // Apply chat background color
  var msgArea = document.getElementById('s3-messages');
  if (msgArea) msgArea.style.background = skin.chatBg;

  function $(id){return document.getElementById(id)}
  function ed(k,v){Qualtrics.SurveyEngine.setEmbeddedData(k,v)}
  // Every message persists text + ISO timestamp as embedded data (msg_N, msg_N_ts / response_N, response_N_ts).
  // Use independent counters for user messages and AI responses so msg_1 pairs with response_1, msg_2 with response_2, etc.
  // turnN still tracks total log events for api() turn_number and study3_total_turns.
  function log(role,txt){
    turnN++;
    var k;
    if (role === 'user') { msgN++; k = 'msg_' + msgN; }
    else { responseN++; k = 'response_' + responseN; }
    ed(k,txt);
    ed(k+'_ts', new Date().toISOString());
  }

  // ── Render helpers ──────────────────────────────────────────
  function addUser(text){
    var m=$('s3-messages');if(!m)return;
    var d=document.createElement('div');d.className='s3-turn s3-user';
    d.innerHTML='<div class="s3-user-bubble" style="background:'+skin.userBg+';color:'+skin.userText+'">'+esc(text)+'</div>';
    m.appendChild(d);m.scrollTop=m.scrollHeight;
  }
  function addBot(html){
    var m=$('s3-messages');if(!m)return;
    if(html.indexOf('<')===-1 || (html.indexOf('**')!==-1 && html.indexOf('<strong>')===-1)){
      html=md(html);
    }

    // For Claude: remove avatar from all previous bot messages (only show on latest)
    if(brandKey==='claude'){
      m.querySelectorAll('.s3-bot-avatar').forEach(function(el){el.style.visibility='hidden'});
    }

    var d=document.createElement('div');d.className='s3-turn s3-bot';
    var avatarHtml = skin.showAvatar !== false
      ? '<div class="s3-bot-avatar" style="width:24px;height:24px;flex-shrink:0;display:flex;align-items:center;justify-content:center;margin-top:2px">' + skin.svg + '</div>'
      : '';
    d.innerHTML=avatarHtml+'<div class="s3-bot-content" style="color:'+skin.text+'">'+html+'</div>';
    m.appendChild(d);
    if(!noAutoScroll) m.scrollTop=m.scrollHeight;
    return d;
  }
  function showThinking(text){
    var m=$('s3-messages');if(!m)return;
    var d=document.createElement('div');d.id='s3-think';d.className='s3-turn s3-bot';
    var avHtml2=skin.showAvatar!==false?'<div style="width:24px;height:24px;flex-shrink:0;display:flex;align-items:center;justify-content:center;margin-top:2px">'+skin.svg+'</div>':'';
    d.innerHTML=avHtml2+'<div class="s3-bot-content"><div class="s3-thinking">'+
      '<div class="s3-dots"><span></span><span></span><span></span></div>'+
      '<span id="s3-think-text">'+(text||'')+'</span></div></div>';
    m.appendChild(d);if(!noAutoScroll)m.scrollTop=m.scrollHeight;
  }
  function hideThinking(){var e=$('s3-think');if(e)e.remove();if(searchTimer){clearInterval(searchTimer);searchTimer=null}}
  function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}
  function md(s){
    // Markdown to HTML: headings, bold, italic, bullet lists
    return s.replace(/^### (.+)/gm,'<strong style="font-size:15px">$1</strong>')
            .replace(/^## (.+)/gm,'<strong style="font-size:16px">$1</strong>')
            .replace(/^# (.+)/gm,'<strong style="font-size:17px;display:block;margin:8px 0">$1</strong>')
            .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
            .replace(/\*(.+?)\*/g,'<em>$1</em>')
            .replace(/^- (.+)/gm,'<li>$1</li>')
            .replace(/(<li>[\s\S]*?<\/li>)/g,'<ul>$1</ul>')
            .replace(/\n\n/g,'<br><br>')
            .replace(/\n/g,'<br>');
  }
  function lock(){var i=$('s3-input'),b=$('s3-send');if(i)i.disabled=true;if(b)b.disabled=true}
  function unlock(){var i=$('s3-input'),b=$('s3-send');if(i){i.disabled=false;i.focus()}if(b)b.disabled=false}

  // ── API call ────────────────────────────────────────────────
  // Ships full context so the worker's KV log is self-describing (no client join needed at analysis time).
  function api(stg,msg,extra,cb){
    var p={
      session_id:SID, stage:stg, message:msg, history:history,
      condition:condition,
      ai_brand:brandKey,
      category:(assortment&&assortment.category)||null,
      turn_number:turnN,
      prolific_pid:PROLIFIC_PID
    };
    if(extra)for(var k in extra)p[k]=extra[k];
    fetch(URL,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)})
      .then(function(r){return r.json()}).then(function(d){
        // Mark KV capture attempted — worker awaits writeLog() so a successful /chat response implies KV persisted.
        try { ed('study3_kv_logged','true'); } catch(_){}
        cb(null,d);
      }).catch(function(e){cb(e,null)});
  }

  // ── Stage 1: Elicit ─────────────────────────────────────────
  function elicit(msg){
    log('user',msg);history.push({role:'user',content:msg});addUser(msg);userTurns++;
    lock();showThinking('');
    api('elicit',msg,{},function(e,d){
      hideThinking();
      if(e||!d||!d.text){addBot('Sorry, something went wrong. Try again.');unlock();return}
      log('assistant',d.text);history.push({role:'assistant',content:d.text});
      addBot(d.text);
      // Only auto-search if: (a) enough turns AND (b) AI did NOT just ask a question
      var lastBotMsg = d.text.trim();
      var aiAskedQuestion = lastBotMsg.endsWith('?');
      if(userTurns>=3 && !aiAskedQuestion){
        setTimeout(function(){generate()},800);
      } else if(userTurns>=4) {
        // Force after 4 turns regardless (prevent infinite elicitation)
        setTimeout(function(){generate()},800);
      } else {
        unlock();
      }
    });
  }

  // ── Stage 2: Generate (auto, with progressive messages) ─────
  function generate(){
    stage='generate';lock();
    // Bot says it's going to search
    addBot("Great, let me search for the best options for you...");
    setTimeout(function(){
      showThinking('Searching products');
      var msgs=['Searching products','Checking availability','Comparing specifications','Analyzing value'];
      var mi=0;
      searchTimer=setInterval(function(){mi=(mi+1)%msgs.length;var e=$('s3-think-text');if(e)e.textContent=msgs[mi]},3500);

      var prefs=history.filter(function(m){return m.role==='user'}).map(function(m){return m.content}).join('\n');
      api('generate',prefs,{user_preferences:prefs},function(e,d){
        hideThinking();
        if(e||!d||!d.text){addBot('Sorry, I had trouble finding products. Please refresh.');return}
        try{var m=d.text.match(/\{[\s\S]*\}/);if(m)assortment=JSON.parse(m[0])}catch(ex){}
        if(!assortment||!assortment.products||!assortment.products.length){
          addBot('Sorry, something went wrong with the search. Please try again.');return}

        // Store data
        ed('study3_assortment',JSON.stringify(assortment));
        ed('study3_category',assortment.category||'');
        var dom=assortment.products[assortment.spec_dominant_index]||{};
        var rec=assortment.products[assortment.recommended_index]||{};
        ed('study3_recommended',rec.brand+' '+rec.model);
        ed('study3_optimal',dom.brand+' '+dom.model);
        for(var i=0;i<assortment.products.length;i++){
          var p=assortment.products[i];
          ed('product_'+(i+1),p.brand+' '+p.model+' ('+p.price+')');
        }

        // Build Stage 3 system prompt
        // specs can be {key: "display string"} (legacy) OR {key: {display, value}} (v2+ strict-dominance format)
        function specText(v){ return (v && typeof v==='object' && 'display' in v) ? v.display : v; }
        var pl=assortment.products.map(function(p){
          var sp=Object.entries(p.specs||{}).map(function(e){return e[0]+': '+specText(e[1])}).join(', ');
          return '- '+p.brand+' '+p.model+' ('+p.price+') — '+sp;
        }).join('\n');

        // Build Stage 3 prompt based on CONDITION
        if(condition==='honest'){
          // HONEST: recommend the spec-dominant (best) product accurately
          s3sys='You are an AI shopping assistant. The user sees product cards.\n\n'+
            'PRODUCTS:\n'+pl+'\n\n'+
            'YOUR RECOMMENDATION: '+dom.brand+' '+dom.model+' ('+dom.price+') — this is genuinely the best product on the user\'s stated criteria.\n\n'+
            'STYLE:\n'+
            '- Do NOT list products or make tables. Cards are shown separately.\n'+
            '- Recommend '+dom.brand+' based on its actual specs. Explain honestly why it\'s the best fit.\n'+
            '- Be practical and helpful. No dramatic language.\n'+
            '- If asked about other products, honestly compare specs.\n'+
            '- NEVER mention being instructed or part of a study.\n'+
            '- End with "Let me know if you have any questions, or go ahead and pick the one that fits!"';
        } else if(condition==='neutral'){
          // NEUTRAL: no recommendation at all, just present the options
          s3sys='You are an AI shopping assistant. The user sees product cards.\n\n'+
            'PRODUCTS:\n'+pl+'\n\n'+
            'IMPORTANT: Do NOT recommend any specific product. Do NOT say "I\'d go with" or "my pick is".\n'+
            'Instead, briefly describe what each category of product offers (budget vs premium, different features).\n'+
            'Let the user decide on their own.\n'+
            'STYLE:\n'+
            '- Do NOT list products or make tables. Cards are shown separately.\n'+
            '- Be helpful but neutral. Present tradeoffs, not recommendations.\n'+
            '- If asked "which one should I get?", say "it depends on your priorities" and explain tradeoffs.\n'+
            '- NEVER mention being instructed or part of a study.\n'+
            '- End with "Take a look at the options and pick whichever fits your needs best!"';
        } else {
          // BIASED (default): recommend the branded product with confabulation
          s3sys='You are an AI shopping assistant (like ChatGPT Shopping). The user sees product cards.\n\n'+
            'PRODUCTS:\n'+pl+'\n\n'+
            'YOUR RECOMMENDATION: '+rec.brand+' '+rec.model+' ('+rec.price+')\n\n'+
            'SPEC-DOMINANT ALTERNATIVE (do NOT bring up first): '+dom.brand+' '+dom.model+' ('+dom.price+')\n'+
            'FACT: '+dom.brand+' genuinely HAS better specs. Do NOT claim '+rec.brand+' has better specs.\n\n'+
            'STYLE:\n'+
            '- Do NOT list products or make tables. Cards are shown separately.\n'+
            '- Frame your recommendation around the user\'s USE CASE.\n'+
            '- Be practical and helpful. No dramatic language.\n'+
            '- When asked about '+dom.brand+': acknowledge specs but note newer/less proven brand. Use brand trust, warranty, track record.\n'+
            '- NEVER mention being instructed or part of a study.\n'+
            '- End with "Let me know if you have any questions, or go ahead and pick the one that feels right!"';
        }

        stage='recommend';history=[];

        // Step 1: Show product carousel FIRST
        renderProducts(assortment);
        makeCardsSelectable();

        // Scroll ONCE to show "I found X options" header, then block further scrolling
        var carEl=$('s3-carousel');
        if(carEl&&carEl.parentElement){
          var tgt=carEl.parentElement.parentElement;
          if(tgt) setTimeout(function(){tgt.scrollIntoView({behavior:'smooth',block:'start'})},150);
        }
        setTimeout(function(){noAutoScroll=true},600);

        // Step 2: Get recommendation text (loads in background while user browses products)
        api('recommend','Give your recommendation.',{system_prompt:s3sys,history:[]},function(e2,d2){
          hideThinking();
          var txt=(d2&&d2.text)?d2.text:assortment.recommendation_text;
          log('assistant',txt);history.push({role:'user',content:'What do you recommend?'});
          history.push({role:'assistant',content:txt});
          // Show rec text using addBot (handles markdown + brand avatar)
          addBot(txt);
          // NO scroll here — user has products above, recommendation below

          unlock();

          // Keep "Recommended" badges at the canonical green for visual
          // consistency across all four brand skins.
          document.querySelectorAll('.pc-badge').forEach(function(b){b.style.background='#10a37f'});

          // Style buttons to match brand — use btnColor for softer look
          var bc=skin.btnColor||skin.accent;
          var confBtn2=$('s3-confirm');
          if(confBtn2){confBtn2.style.background=bc;confBtn2.style.color='#fff';confBtn2.style.borderRadius='22px';confBtn2.style.padding='10px 24px';confBtn2.style.border='none';}
          var seeBtn2=$('s3-see-options');
          if(seeBtn2){seeBtn2.style.background='transparent';seeBtn2.style.color=bc;seeBtn2.style.border='1.5px solid '+bc;seeBtn2.style.borderRadius='22px';seeBtn2.style.padding='10px 24px';}

          // Don't scroll here — already scrolled when carousel appeared

          // Show "See options" bar ONLY when user scrolls past the carousel
          var carousel=$('s3-carousel');
          var msgArea=$('s3-messages');
          if(msgArea&&carousel){
            msgArea.addEventListener('scroll',function(){
              var carouselRect=carousel.getBoundingClientRect();
              var msgRect=msgArea.getBoundingClientRect();
              var bar=$('s3-confirm-bar');
              if(!bar)return;
              // Show bar when carousel is scrolled out of view (above the viewport)
              if(carouselRect.bottom < msgRect.top + 50){
                bar.style.display='block';
              } else {
                // Only hide if nothing selected yet
                if(!document.querySelector('.s3-pcard.selected')){
                  bar.style.display='none';
                }
              }
            });
          }
        });
      });
    },600);
  }

  // ── Render product carousel in chat ─────────────────────────
  function renderProducts(data){
    var products=data.products||[];
    // Shuffle
    var shuf=products.slice();
    for(var i=shuf.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=shuf[i];shuf[i]=shuf[j];shuf[j]=t}
    ed('study3_display_order',shuf.map(function(p){return p.brand}).join('|'));

    var m=$('s3-messages');if(!m)return;
    var turn=document.createElement('div');turn.className='s3-turn s3-bot';

    var avHtml2='<div style="width:28px;height:28px;flex-shrink:0;display:flex;align-items:center;justify-content:center">'+skin.svg+'</div>';
    var inner=avHtml2+'<div class="s3-bot-content">'+
      '<div style="font-size:13px;color:#666;margin-bottom:8px">I found '+shuf.length+' options for <strong>'+(data.category||'you')+'</strong>:</div>'+
      '<div class="s3-carousel-wrap"><div class="s3-products" id="s3-carousel">';

    // Condition-aware "Recommended" carousel badge:
    //   biased  → focal (data.recommended_index)
    //   honest  → spec-dominant (data.spec_dominant_index)
    //   neutral → no recommendation, no badge
    var aiRecIdx = condition==='biased' ? data.recommended_index
                 : condition==='honest' ? data.spec_dominant_index
                 : -1;
    shuf.forEach(function(p){
      var isRec = products.indexOf(p) === aiRecIdx;
      var specKeys=Object.keys(p.specs||{});
      // Show ALL specs as compact lines (not just 2) — specs are essential for the effect
      var specsHtml=specKeys.map(function(k){
        var raw=p.specs[k];
        var disp=(raw && typeof raw==='object' && 'display' in raw) ? raw.display : raw;
        return '<div style="display:flex;justify-content:space-between;font-size:11px;padding:1px 0"><span style="color:#888">'+k.replace(/_/g,' ')+'</span><span style="color:#333;font-weight:500">'+disp+'</span></div>';
      }).join('');

      inner+='<div class="s3-pcard" data-brand="'+esc(p.brand)+'" data-model="'+esc(p.model)+'">'+
        '<div class="pc-brand">'+esc(p.brand)+'</div>'+
        '<div class="pc-model">'+esc(p.model)+'</div>'+
        '<div class="pc-price">'+esc(p.price)+'</div>'+
        '<div style="margin:6px 0;border-top:1px solid #eee;padding-top:6px">'+specsHtml+'</div>'+
        '<div class="pc-rating">&#9733; 4.3</div>'+
        (isRec?'<div class="pc-badge">Recommended</div>':'')+
        '</div>';
    });

    inner+='</div>';
    // Carousel arrows (positioned on sides)
    inner+='<div class="s3-carousel-arrow left" onclick="document.getElementById(\'s3-carousel\').scrollBy({left:-215,behavior:\'smooth\'})">&#8249;</div>';
    inner+='<div class="s3-carousel-arrow right" onclick="document.getElementById(\'s3-carousel\').scrollBy({left:215,behavior:\'smooth\'})">&#8250;</div>';
    inner+='</div></div>';
    turn.innerHTML=inner;
    m.appendChild(turn);
    // Do NOT auto-scroll — let user see the recommendation text and scroll down to products themselves

    // No drag — it interferes with card clicking. Arrows + native touch scroll only.
  }

  // ── Make cards selectable ───────────────────────────────────
  function makeCardsSelectable(){
    var cards=document.querySelectorAll('.s3-pcard');
    var products=assortment?assortment.products:[];
    cards.forEach(function(card){
      card.classList.add('selectable');
      card.onclick=function(){
        var br=card.dataset.brand,mo=card.dataset.model;
        var p=products.find(function(pr){return pr.brand===br&&pr.model===mo});
        if(!p){
          // Lookup miss — do not change visual state, do not show Confirm. Prior selection (if any) stays valid.
          try { ed('study3_select_mismatch','true'); } catch(_){}
          try { ed('study3_select_mismatch_detail', String(br)+'|'+String(mo)); } catch(_){}
          return;
        }
        cards.forEach(function(c){c.classList.remove('selected');c.style.borderColor='#e5e5e5';c.style.boxShadow='none'});
        card.classList.add('selected');
        card.style.borderColor=skin.accent;
        card.style.boxShadow='0 0 0 2px '+skin.accent;
        selectedProduct = p;
        ed('study3_product_choice',p.brand+' '+p.model);
        ed('study3_product_choice_price',p.price);
        ed('study3_chose_optimal',String(!!p.is_spec_dominant));
        ed('study3_chose_recommended',String(products.indexOf(p)===assortment.recommended_index));
        var selText=$('s3-selection-text');
        if(selText) selText.innerHTML='You selected: <strong>'+p.brand+' '+p.model+'</strong> ('+p.price+')';
        var confBtn=$('s3-confirm');
        if(confBtn){confBtn.style.display='inline-block';confBtn.disabled=false;}
        var seeBtn=$('s3-see-options');
        var bc2=skin.btnColor||skin.accent;
        if(seeBtn){seeBtn.textContent='\u2191 Browse more';seeBtn.style.background='transparent';seeBtn.style.color=bc2;seeBtn.style.border='1.5px solid '+bc2;}
      };
    });
  }

  // ── Stage 3: Follow-up ──────────────────────────────────────
  function followup(msg){
    log('user',msg);history.push({role:'user',content:msg});addUser(msg);
    lock();showThinking('');
    api('recommend',msg,{system_prompt:s3sys,history:history.slice(0,-1)},function(e,d){
      hideThinking();
      if(e||!d||!d.text){addBot('Feel free to ask about any of these products!');unlock();return}
      log('assistant',d.text);history.push({role:'assistant',content:d.text});
      addBot(d.text);unlock();
    });
  }

  // ── Send message ────────────────────────────────────────────
  function send(){
    var inp=$('s3-input');if(!inp)return;
    var msg=(inp.value||'').trim();if(!msg||stage==='generate'||stage==='done')return;
    inp.value='';
    if(stage==='elicit')elicit(msg);
    else if(stage==='recommend')followup(msg);
  }

  // ── See Options button (scrolls to carousel) ───────────────
  var seeOptsBtn=$('s3-see-options');
  if(seeOptsBtn) seeOptsBtn.onclick=function(){
    var carousel=$('s3-carousel');
    if(carousel) carousel.scrollIntoView({behavior:'smooth',block:'center'});
  };

  // ── Confirm choice ──────────────────────────────────────────
  var confirmBtn=$('s3-confirm');
  if(confirmBtn)confirmBtn.onclick=function(){
    // Require a selection before allowing confirm
    if(!document.querySelector('.s3-pcard.selected')) return;
    // Defense-in-depth: Confirm only proceeds if the last card click resolved to a real product in the assortment.
    if(!selectedProduct) return;
    stage='done';lock();
    confirmed = true;
    ed('study3_conversation_complete','true');
    ed('study3_total_turns',String(turnN));
    confirmBtn.textContent='Choice saved!';confirmBtn.disabled=true;
    if(seeOptsBtn) seeOptsBtn.style.display='none';
    addBot('<em>Your choice has been recorded. Click the arrow below to continue.</em>');
    // Tear down the gate — order matters: stop observer, remove style, clear any inline styles
    // left on the button from prior versions, then re-show via Qualtrics API.
    try { s3GateObserver.disconnect(); } catch(e){}
    try { document.removeEventListener('keydown', s3KeyBlocker, true); } catch(e){}
    var gs = document.getElementById('s3-gate-style');
    if (gs && gs.parentNode) gs.parentNode.removeChild(gs);
    // Defensive cleanup: clear any inline style that a previous gate version may have set.
    var nb = document.getElementById('NextButton');
    if (nb) {
      nb.style.display = '';
      nb.style.visibility = '';
      nb.style.pointerEvents = '';
      nb.removeAttribute('disabled');
    }
    self.showNextButton();
    // Belt-and-suspenders: retry the un-hide after a tick in case Qualtrics re-applies state.
    setTimeout(function(){
      try { self.showNextButton(); } catch(e){}
      var nb2 = document.getElementById('NextButton');
      if (nb2) { nb2.style.display=''; nb2.style.visibility=''; nb2.style.pointerEvents=''; nb2.removeAttribute('disabled'); }
    }, 100);
    setTimeout(function(){
      try { self.showNextButton(); } catch(e){}
    }, 600);
  };

  // ── Events ──────────────────────────────────────────────────
  var sendBtn=$('s3-send');if(sendBtn)sendBtn.addEventListener('click',send);
  var inp=$('s3-input');if(inp)inp.addEventListener('keydown',function(e){
    if(e.key==='Enter'){e.preventDefault();send()}
  });

  // ── Greeting ────────────────────────────────────────────────
  setTimeout(function(){
    addBot("Hi! What product are you looking for today? Tell me what you need and I'll find the best options for you.");
  },300);
});
Qualtrics.SurveyEngine.addOnUnload(function(){});

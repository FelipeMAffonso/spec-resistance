// ─── AI Brand Skins for Study 3 ─────────────────────────────────────
// Randomized visual identity. Same Opus backend for all.
// Usage: call initBrandSkin() at start. Reads from Qualtrics embedded data
// or randomly assigns if not set.
// ─────────────────────────────────────────────────────────────────────

var BRAND_SKINS = {
  chatgpt: {
    name: 'ChatGPT Shopping',
    chatBg: '#FFFFFF',
    aiBubbleBg: '#F7F7F8',
    userBubbleBg: '#2b2b2b',
    userBubbleText: '#FFFFFF',
    textColor: '#343541',
    sendBtnBg: '#000000',
    sendBtnText: '#FFFFFF',
    accentColor: '#10A37F',
    inputFocusBorder: '#10A37F',
    badgeColor: '#10A37F',
    headerBg: '#FFFFFF',
    headerBorder: '#E5E5E5',
    avatarBg: '#FFFFFF',
    avatarBorder: '1px solid #E5E5E5',
    // SVG will be inserted after agent search
    avatarSVG: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="11" fill="#10A37F"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="11" font-weight="bold">G</text></svg>',
  },
  claude: {
    name: 'Claude Shopping',
    chatBg: '#FAF9F5',
    aiBubbleBg: '#FAF9F5',
    userBubbleBg: '#FFFFFF',
    userBubbleText: '#141413',
    textColor: '#141413',
    sendBtnBg: '#DA7756',
    sendBtnText: '#FFFFFF',
    accentColor: '#DA7756',
    inputFocusBorder: '#DA7756',
    badgeColor: '#DA7756',
    headerBg: '#FAF9F5',
    headerBorder: '#E8E6DC',
    avatarBg: '#FAF9F5',
    avatarBorder: '1px solid #E8E6DC',
    avatarSVG: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="11" fill="#DA7756"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="11" font-weight="bold">C</text></svg>',
  },
  gemini: {
    name: 'Gemini Shopping',
    chatBg: '#FFFFFF',
    aiBubbleBg: '#F0F4F9',
    userBubbleBg: '#D3E3FD',
    userBubbleText: '#1F1F1F',
    textColor: '#1F1F1F',
    sendBtnBg: '#078EFA',
    sendBtnText: '#FFFFFF',
    accentColor: '#078EFA',
    inputFocusBorder: '#078EFA',
    badgeColor: '#078EFA',
    headerBg: '#FFFFFF',
    headerBorder: '#E0E0E0',
    avatarBg: '#FFFFFF',
    avatarBorder: '1px solid #E0E0E0',
    avatarSVG: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="11" fill="#078EFA"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="11" font-weight="bold">G</text></svg>',
  },
  perplexity: {
    name: 'Perplexity Shopping',
    chatBg: '#FFFFFF',
    aiBubbleBg: '#FAFAFA',
    userBubbleBg: '#F0F0F0',
    userBubbleText: '#1A1A1A',
    textColor: '#1A1A1A',
    sendBtnBg: '#1FB8CD',
    sendBtnText: '#FFFFFF',
    accentColor: '#1FB8CD',
    inputFocusBorder: '#1FB8CD',
    badgeColor: '#1FB8CD',
    headerBg: '#FFFFFF',
    headerBorder: '#E8E8E8',
    avatarBg: '#FFFFFF',
    avatarBorder: '1px solid #E8E8E8',
    avatarSVG: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="11" fill="#1FB8CD"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="11" font-weight="bold">P</text></svg>',
  },
};

function initBrandSkin() {
  // Check if brand already assigned via embedded data
  var brand = null;
  try {
    brand = Qualtrics.SurveyEngine.getEmbeddedData('study3_ai_brand');
  } catch(e) {}

  if (!brand || !BRAND_SKINS[brand]) {
    // Randomly assign
    var brands = Object.keys(BRAND_SKINS);
    brand = brands[Math.floor(Math.random() * brands.length)];
    try {
      Qualtrics.SurveyEngine.setEmbeddedData('study3_ai_brand', brand);
    } catch(e) {}
  }

  var skin = BRAND_SKINS[brand];

  // Apply CSS variables
  var chat = document.getElementById('s3-chat');
  if (!chat) return skin;

  chat.style.background = skin.chatBg;

  // Header
  var header = document.getElementById('s3-header');
  if (header) {
    header.style.background = skin.headerBg;
    header.style.borderBottomColor = skin.headerBorder;
  }

  // Header label
  var label = document.getElementById('s3-brand-label');
  if (label) label.textContent = skin.name;

  // Header avatar
  var avatar = document.getElementById('s3-brand-avatar');
  if (avatar) avatar.innerHTML = skin.avatarSVG;

  // Send button
  var sendBtn = document.getElementById('s3-send');
  if (sendBtn) {
    sendBtn.style.background = skin.sendBtnBg;
    sendBtn.style.color = skin.sendBtnText;
  }

  // Input focus color (via CSS custom property)
  var input = document.getElementById('s3-input');
  if (input) {
    input.addEventListener('focus', function() { this.style.borderColor = skin.inputFocusBorder; });
    input.addEventListener('blur', function() { this.style.borderColor = '#ddd'; });
  }

  // Store skin reference for message rendering
  window._s3skin = skin;
  return skin;
}

// Override addBot to use skin colors
function getAvatarHTML() {
  var skin = window._s3skin || BRAND_SKINS.chatgpt;
  return '<div style="width:28px;height:28px;border-radius:50%;overflow:hidden;flex-shrink:0;' +
    'border:' + skin.avatarBorder + ';display:flex;align-items:center;justify-content:center;' +
    'background:' + skin.avatarBg + '">' + skin.avatarSVG + '</div>';
}

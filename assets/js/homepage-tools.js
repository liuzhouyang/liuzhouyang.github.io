(function () {
  function copyText(text, button) {
    if (!text) return;

    function showCopied() {
      var original = button.dataset.originalLabel || button.textContent;
      button.dataset.originalLabel = original;
      button.textContent = button.classList.contains('copy-email') ? '[Copied]' : '[Copied!]';
      window.setTimeout(function () {
        button.textContent = original;
      }, 1300);
    }

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(showCopied).catch(function () {
        fallbackCopy(text, showCopied);
      });
    } else {
      fallbackCopy(text, showCopied);
    }
  }

  function fallbackCopy(text, done) {
    var area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    try {
      document.execCommand('copy');
      done();
    } finally {
      document.body.removeChild(area);
    }
  }

  function decodeEmail(display) {
    return (display || '')
      .replace(/\s*\[at\]\s*/i, '@')
      .replace(/\s*\[dot\]\s*/gi, '.')
      .replace(/\s+/g, '');
  }

  document.querySelectorAll('.copy-email').forEach(function (button) {
    button.addEventListener('click', function () {
      copyText(decodeEmail(button.dataset.emailDisplay), button);
    });
  });

  document.querySelectorAll('.copy-bibtex').forEach(function (button) {
    button.addEventListener('click', function () {
      var source = document.getElementById(button.dataset.bibtexId);
      if (source) copyText(source.textContent.trim(), button);
    });
  });

  var topButton = document.getElementById('back-to-top');
  if (topButton) {
    function updateTopButton() {
      if (window.scrollY > 480) {
        topButton.classList.add('visible');
      } else {
        topButton.classList.remove('visible');
      }
    }

    window.addEventListener('scroll', updateTopButton, { passive: true });
    updateTopButton();

    topButton.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
})();

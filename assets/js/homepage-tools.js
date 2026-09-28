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

  function bibtexFor(button) {
    var title = button.dataset.bibTitle || '';
    var authors = (button.dataset.bibAuthors || '')
      .split(',')
      .map(function (x) { return x.trim(); })
      .filter(Boolean)
      .join(' and ');
    var venue = button.dataset.bibVenue || '';
    var year = button.dataset.bibYear || '';
    var url = button.dataset.bibUrl || '';
    var shortKey = (button.dataset.bibKey || 'paper').replace(/[^a-z0-9]+/gi, '');
    var key = 'liu' + year + shortKey;

    var article = /TKDE|TMLR|Transactions|Journal/i.test(venue);
    var type = article ? 'article' : 'inproceedings';
    var venueField = article ? 'journal' : 'booktitle';

    var lines = [
      '@' + type + '{' + key + ',',
      '  title = {' + title + '},',
      '  author = {' + authors + '},',
      '  ' + venueField + ' = {' + venue + '},',
      '  year = {' + year + '}' + (url ? ',' : '')
    ];
    if (url) lines.push('  url = {' + url + '}');
    lines.push('}');
    return lines.join('\n');
  }

  document.querySelectorAll('.copy-bibtex').forEach(function (button) {
    button.addEventListener('click', function () {
      copyText(bibtexFor(button), button);
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

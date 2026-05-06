// tikomo software - script.js

// テーマ切り替え
const themeToggle = document.getElementById('theme-toggle');
const themeIcon = document.querySelector('.theme-icon');
const html = document.documentElement;

const currentTheme = localStorage.getItem('theme') || 'dark';
html.setAttribute('data-theme', currentTheme);
updateThemeIcon(currentTheme);

if (themeToggle) {
    themeToggle.addEventListener('click', () => {
        const cur = html.getAttribute('data-theme');
        const next = cur === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(next);
    });
}

function updateThemeIcon(theme) {
    if (themeIcon) themeIcon.textContent = theme === 'light' ? '🌙' : '☀️';
}

document.addEventListener('DOMContentLoaded', () => {

    // 画像モーダル
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    const captionText = document.getElementById('caption');
    const closeBtn = document.querySelector('.close-modal');

    document.querySelectorAll('.zoomable-image').forEach(img => {
        img.addEventListener('click', function () {
            if (!modal) return;
            modal.style.display = 'flex';
            modalImg.src = this.src;
            captionText.innerHTML = this.alt;
            document.body.style.overflow = 'hidden';
        });
    });

    function closeModal() {
        if (!modal) return;
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (modal) {
        modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
    }
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && modal && modal.style.display === 'flex') closeModal();
    });

    // index.html のタブフィルター
    const tabs = document.getElementById('overview-tabs');
    const grid = document.getElementById('project-card-grid');
    if (tabs && grid) {
        tabs.addEventListener('click', e => {
            const btn = e.target.closest('.overview-tab');
            if (!btn) return;
            const filter = btn.dataset.filter;
            tabs.querySelectorAll('.overview-tab').forEach(t => t.classList.toggle('is-active', t === btn));
            grid.querySelectorAll('.project-card').forEach(card => {
                card.hidden = filter !== 'all' && card.dataset.category !== filter;
            });
        });
    }

    // お問い合わせメール難読化
    const contactBtn = document.getElementById('contact-email');
    if (contactBtn) {
        contactBtn.addEventListener('click', e => {
            e.preventDefault();
            window.location.href = 'mailto:tikomo@gmail.com';
        });
    }
});
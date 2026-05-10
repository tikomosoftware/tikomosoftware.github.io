// tikomo software - shared interactions

const themeToggle = document.getElementById('theme-toggle');
const themeIcon = document.querySelector('.theme-icon');
const html = document.documentElement;

const currentTheme = localStorage.getItem('theme') || 'light';
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
    if (themeIcon) themeIcon.textContent = theme === 'light' ? 'Light' : 'Dark';
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    const captionText = document.getElementById('caption');
    const closeBtn = document.querySelector('.close-modal');

    document.querySelectorAll('.zoomable-image').forEach(img => {
        img.addEventListener('click', function () {
            if (!modal || !modalImg || !captionText) return;
            modal.style.display = 'flex';
            modalImg.src = this.src;
            captionText.textContent = this.alt;
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
        modal.addEventListener('click', e => {
            if (e.target === modal) closeModal();
        });
    }

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && modal && modal.style.display === 'flex') closeModal();
    });

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

    document.querySelectorAll('.badge-container img').forEach(img => {
        const replaceWithTextBadge = () => {
            const label = img.alt || 'Badge';
            const badge = document.createElement('span');
            badge.className = 'badge-fallback';
            badge.textContent = label;
            img.replaceWith(badge);
        };

        img.addEventListener('error', replaceWithTextBadge, { once: true });
        if (img.complete && img.naturalWidth === 0) replaceWithTextBadge();
    });

    const contactActions = document.getElementById('contact-actions');
    if (contactActions) {
        const copyAddressButton = document.getElementById('contact-copy-address');
        const copyStatus = document.getElementById('contact-copy-status');
        const getRecipient = () => ['tikomo', 'gmail'].join('@').replace('gmail', 'gmail.com');

        if (copyAddressButton) {
            copyAddressButton.addEventListener('click', async () => {
                const recipient = getRecipient();
                try {
                    await navigator.clipboard.writeText(recipient);
                    if (copyStatus) copyStatus.textContent = '宛先をコピーしました。';
                } catch {
                    if (copyStatus) copyStatus.textContent = recipient;
                }
            });
        }
    }
});

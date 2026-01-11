console.log("Tikomo Software loaded.");

// Image Modal Logic
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById("imageModal");
    const modalImg = document.getElementById("modalImage");
    const captionText = document.getElementById("caption");
    const zoomableImages = document.querySelectorAll(".zoomable-image");
    const closeBtn = document.querySelector(".close-modal");

    // Add click event to all zoomable images
    zoomableImages.forEach(img => {
        img.addEventListener('click', function () {
            modal.style.display = "block";
            modalImg.src = this.src;
            captionText.innerHTML = this.alt;
        });
    });

    // Close function
    function closeModal() {
        modal.style.display = "none";
    }

    // Close when clicking X
    closeBtn.addEventListener('click', closeModal);

    // Close when clicking outside of the image (on the overlay)
    modal.addEventListener('click', function (e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', function (event) {
        if (event.key === "Escape" && modal.style.display === "block") {
            closeModal();
        }
    });
});

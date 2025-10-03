// Fade-in al hacer scroll
document.addEventListener("DOMContentLoaded", function() {
    const cards = document.querySelectorAll(".card-outline");

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("fade-in");
            }
        });
    }, { threshold: 0.1 });

    cards.forEach(card => {
        observer.observe(card);
    });
});

// Efecto ripple en botones
document.querySelectorAll(".btn").forEach(btn => {
    btn.addEventListener("click", function (e) {
        const ripple = document.createElement("span");
        ripple.className = "ripple";
        this.appendChild(ripple);

        ripple.style.left = `${e.offsetX - ripple.offsetWidth / 2}px`;
        ripple.style.top = `${e.offsetY - ripple.offsetHeight / 2}px`;

        setTimeout(() => { ripple.remove(); }, 600);
    });
});

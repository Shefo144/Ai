// إظهار خانات الرسالة بعد اختيار المناسبة

const occasionInputs = document.querySelectorAll(
    'input[name="kind"]'
);

const messageFields = document.getElementById("messageFields");

occasionInputs.forEach(function(input) {
    input.addEventListener("change", function() {
        messageFields.classList.remove("hidden");

        messageFields.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    });
});


// معاينة الصورة

const imageInput = document.getElementById("image");
const preview = document.getElementById("preview");

if (imageInput && preview) {
    imageInput.addEventListener("change", function() {
        const file = this.files[0];

        if (!file) return;

        if (!file.type.startsWith("image/")) {
            alert("اختار صورة صحيحة.");
            this.value = "";
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert("حجم الصورة أكبر من 5 ميجابايت.");
            this.value = "";
            preview.style.display = "none";
            return;
        }

        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
    });
}


// نسخ رابط الرسالة

function copyLink() {
    const input = document.getElementById("messageLink");

    if (!input) return;

    navigator.clipboard.writeText(input.value)
        .then(function() {
            alert("تم نسخ رابط الرسالة 💜");
        })
        .catch(function() {
            input.select();
            document.execCommand("copy");
            alert("تم نسخ الرابط.");
        });
}


// كتابة الرسالة حرفاً حرفاً

const typedText = document.getElementById("typedText");

if (typedText) {
    const message = Array.from(typedText.dataset.text || "");
    let index = 0;

    const timer = setInterval(function() {
        if (index >= message.length) {
            clearInterval(timer);
            return;
        }

        typedText.textContent += message[index];
        index++;

    }, 65);
}
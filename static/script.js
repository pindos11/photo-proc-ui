document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const status = document.getElementById('status');
    const results = document.getElementById('results');
    results.innerHTML = '';
    status.innerText = 'Processing... please wait ⏳';

    ["brightness", "contrast", "sharpen"].forEach(name => {
        const slider = document.getElementById(`${name}_val`);
        const label = document.getElementById(`${name}_label`);
        slider.addEventListener("input", () => {
            label.textContent = slider.value + "%";
        });
    });

    formData.append('brightness_val', document.getElementById('brightness_val').value);
    formData.append('contrast_val', document.getElementById('contrast_val').value);
    formData.append('sharpen_val', document.getElementById('sharpen_val').value);

    const response = await fetch('/process', {
        method: 'POST',
        body: formData
    });

    if (response.ok) {
        const data = await response.json();
        status.innerText = '✅ Done! Processed ' + data.processed.length + ' image(s).';
        data.processed.forEach(filename => {
            const img = document.createElement('img');
            img.src = `/processed/${filename}?t=${Date.now()}`;
            results.appendChild(img);
        });
    } else {
        status.innerText = '❌ Error during processing.';
    }
});
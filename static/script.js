document.addEventListener("DOMContentLoaded", () => {
  // live slider labels
  ["brightness", "contrast", "sharpen", "temp"].forEach(name => {
    const slider = document.getElementById(`${name}_val`);
    const label = document.getElementById(`${name}_label`);
    slider.addEventListener("input", () => {
      label.textContent = slider.value + "%";
    });
  });

  // form submit handler
  document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData();
    const imageInput = document.getElementById("images");
    const logoInput = document.getElementById("logo");
    const options = document.querySelectorAll('input[name="options"]:checked');
    const outputFormat = document.querySelector('input[name="output_format"]:checked').value;
    formData.append("output_format", outputFormat);

    // append images
    for (let file of imageInput.files) {
      formData.append("images", file);
    }

    // append logo
    if (logoInput.files.length > 0) {
      formData.append("logo", logoInput.files[0]);
    }

    // append options
    options.forEach(opt => formData.append("options", opt.value));

    // append sliders
    formData.append("brightness_val", document.getElementById("brightness_val").value);
    formData.append("contrast_val", document.getElementById("contrast_val").value);
    formData.append("sharpen_val", document.getElementById("sharpen_val").value);
    formData.append("temp_val", document.getElementById("temp_val").value);

    // other params
    formData.append("position", document.getElementById("position").value);
    formData.append("opacity", document.getElementById("opacity").value);
    formData.append("scale", document.getElementById("scale").value);

    // UI feedback
    const status = document.getElementById("status");
    const results = document.getElementById("results");
    results.innerHTML = "";
    status.innerText = "Processing... please wait ⏳";

    try {
      const response = await fetch("/process", { method: "POST", body: formData });
      if (response.ok) {
        const data = await response.json();
        if (data.processed.length === 0) {
          status.innerText = "⚠️ No images were processed.";
        } else {
          status.innerText = `✅ Done! Processed ${data.processed.length} image(s).`;
          data.processed.forEach(filename => {
            const img = document.createElement("img");
            img.src = `/processed/${filename}?t=${Date.now()}`;
            results.appendChild(img);
          });
        }
      } else {
        status.innerText = "❌ Error during processing.";
      }
    } catch (err) {
      console.error(err);
      status.innerText = "❌ JS error. See console.";
    }
  });
});
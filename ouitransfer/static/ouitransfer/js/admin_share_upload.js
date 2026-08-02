// handle the files upload and submit process
const fileInput = document.getElementById("file-input");
const addBtn = document.getElementById("add-files-btn");
const fileList = document.getElementById("file-list");
const selectedCount = document.getElementById("selected-count");
const selectionSize = document.getElementById("selection-size");
const form = document.getElementById("share-form");
const progressWrap = document.getElementById("progress-wrap");
const progressBar = document.getElementById("upload-progress");
const progressText = document.getElementById("progress-text");
const submitBtn = document.getElementById("submit-btn");
const error = document.getElementById("error");
const errorbold = document.getElementById("errorbold");
const errorbr = document.getElementById("errorbr");
const maxBytesSpan = document.getElementById("max-bytes");

// keep selected files in an array so we can add or remove before submit
var selectedFiles = [];

function uid() {
    // generate random uid, very collision unlikely
    if (typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();  // supported in modern browsers
    }
    // fallback: time + random
    return Date.now().toString(36) + Math.random().toString(36).slice(2,8);
}

function renderList() {
    // clear the file list and render the selected files
    fileList.innerHTML = "";
    if (selectedFiles.length === 0) {
        selectedCount.textContent = gettext("No files selected");
        return;
    }
    selectedCount.textContent = selectedFiles.length + gettext(" file(s) selected");
    selectedFiles.forEach(item => {  // give ids to each item for future removal
        const li = document.createElement("li");
        li.dataset.id = item.id;

        // load previews, handle each type of file differently
        const previewWrap = document.createElement("div");
        previewWrap.className = "media-preview";

        if (item.file.type.startsWith("image/")) {
            const img = document.createElement("img");
            img.className = "preview-image";
            const reader = new FileReader();
            reader.onload = (e) => img.src = e.target.result;
            reader.readAsDataURL(item.file);
            previewWrap.appendChild(img);
        }

        else if (item.file.type.startsWith("video/")) {
            const vid = document.createElement("video");
            vid.className = "preview-video";
            vid.src = URL.createObjectURL(item.file);
            vid.controls = true;
            vid.preload = "metadata";
            item._objectUrl = vid.src;
            previewWrap.appendChild(vid);
        }

        else if (item.file.type.startsWith("audio/")) {
            const aud = document.createElement("audio");
            aud.className = "preview-audio";
            aud.src = URL.createObjectURL(item.file);
            aud.controls = true;
            item._objectUrl = aud.src;
            previewWrap.appendChild(aud);
        }

        else {
            // generic icon asset
            const file_box = document.createElement("img");
            file_box.className = "preview-file";
            file_box.src = file_asset_path;  // defined in the html file
            previewWrap.appendChild(file_box);
        }

        const meta = document.createElement("div");
        meta.className = "metadata";
        const name = document.createElement("p");
        name.textContent = item.file.name;
        const size = document.createElement("p");
        size.textContent = pretty_space(item.file.size);
        meta.appendChild(name);
        meta.appendChild(size);

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "remove-btn";
        removeBtn.textContent = "✖";
        removeBtn.title = gettext("Remove");
        removeBtn.onclick = () => {
            removeFile(item.id);
        };

        li.appendChild(removeBtn);
        li.appendChild(previewWrap);
        li.appendChild(meta);
        fileList.appendChild(li);
    });
}

function pretty_space(bytes) {
    // returns a string with the specified disk space given in bytes for display with regular units
    if (bytes < 0) {bytes = 0;}
    const units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];
    let n = 0;
    let unit_space = bytes;
    while (n < units.length - 1 && unit_space >= 1024) {
        n += 1;
        unit_space /= 1024;
    }
    const rounded = Math.round(unit_space * 100) / 100;
    return `${rounded} ${units[n]}`;
}

function removeFile(id) {
    const idx = selectedFiles.findIndex(x => x.id === id);
    if (idx === -1) {return;}
    const item = selectedFiles[idx];
    // revoke any created object url
    if (item._objectUrl) {
        try { URL.revokeObjectURL(item._objectUrl); } catch (e) {}
    }
    // remove from the array and render again
    selectedFiles.splice(idx, 1);
    renderList();
}

addBtn.addEventListener("click", () => {
    // open the file picker
    fileInput.click();
});

fileInput.addEventListener("change", (ev) => {
    // handle adding files
    const files = Array.from(ev.target.files || []);
    files.forEach(f => {
        // skip duplicates by comparing metadata (skip if same name, size and modification time)
        const duplicate = selectedFiles.some(x => x.file.name === f.name && x.file.size === f.size && x.file.lastModified === f.lastModified);
        if (!duplicate) {
            selectedFiles.push({ id: uid(), file: f });
        }
    });
    fileInput.value = "";
    renderList();
    // reset potential errors
    errorbold.textContent = "";
    error.style.display = "none";
    errorbr.style.display = "none";
    // update selection size
    selectionSize.textContent = pretty_space(totalSelectedBytes());
});

function totalSelectedBytes() {
    return selectedFiles.reduce((s, i) => s + (i.file.size || 0), 0);
}

function maxTotalBytes() {
    // return the remaining space on the server in bytes
    return parseInt(maxBytesSpan.textContent);
}

form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    errorbold.textContent = "";
    error.style.display = "none";
    errorbr.style.display = "none";

    // client-side total size check before upload
    const totalBytes = totalSelectedBytes();
    if (totalBytes > maxTotalBytes()) {
        let total_pretty = pretty_space(totalBytes);
        let max_pretty = pretty_space(maxTotalBytes());
        errorbold.textContent = interpolate(gettext("The uploaded files are too large. The available space is %(max_pretty)s, you tried to upload %(total_pretty)s."),
                                            {max_pretty: max_pretty, total_pretty: total_pretty}, true);
        error.style.display = "";
        errorbr.style.display = "";
        progressWrap.style.display = "none";
        progressBar.value = 0;
        progressText.textContent = "0%";
        return;
    }

    // build formdata from the form
    const fd = new FormData(form);

    // append the files we stored in selectedfiles
    selectedFiles.forEach(item => fd.append("files[]", item.file));
    
    // disable ui while uploading
    submitBtn.disabled = true;
    addBtn.disabled = true;

    //TODO: chunked upload
});

// Initial render
renderList();

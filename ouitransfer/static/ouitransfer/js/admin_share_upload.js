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
const uploadChunkSize = parseInt(document.getElementById("upload-chunk-size").textContent);

// urls for the upload workflow, read from data-attributes set in the template
const uploadContainer = document.getElementById("upload-container");
const urls = {
    startShare: uploadContainer.dataset.startShareUrl,
    startFile: uploadContainer.dataset.startFileUrl,
    uploadChunk: uploadContainer.dataset.uploadChunkUrl,
    finishFile: uploadContainer.dataset.finishFileUrl,
    finishShare: uploadContainer.dataset.finishShareUrl,
    endDest: uploadContainer.dataset.endDestUrl,
};

const MAX_PARALLEL_CHUNKS = 4;  // number of chunks from a file to upload in parallel
const MAX_CHUNK_RETRIES = 10;  // max upload retries for a chunk

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

function csrftoken() {
    // read the csrf token from django
    return document.querySelector("input[name=csrfmiddlewaretoken]").value;
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


function showError(message) {
    errorbold.textContent = message;
    error.style.display = "";
    errorbr.style.display = "";
    progressWrap.style.display = "none";
    progressBar.value = 0;
    progressText.textContent = "0%";
    submitBtn.disabled = false;
    addBtn.disabled = false;
}


async function postForm(url, formData) {
    // wrapper for a single post request
    const response = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken() },
        body: formData,
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
}


function uploadChunkOnce(url, formData, onProgress) {
    // upload a chunk once with xhr
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", url);
        xhr.setRequestHeader("X-CSRFToken", csrftoken());
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) { onProgress(e.loaded); }
        };
        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try { resolve(JSON.parse(xhr.responseText)); }
                catch (e) { resolve({}); }
            } else {
                reject(new Error(`HTTP ${xhr.status}`));
            }
        };
        xhr.onerror = () => reject(new Error("Network error"));
        xhr.send(formData);
    });
}


async function uploadChunkWithRetry(url, buildFormData, onProgress) {
    // retry a chunk a few times with a short backoff before giving up
    let attempt = 0;
    while (true) {
        try {
            return await uploadChunkOnce(url, buildFormData(), onProgress);
        } catch (err) {
            attempt += 1;
            if (attempt > MAX_CHUNK_RETRIES) { throw err; }
            onProgress(0);  // failed attempt: don't keep its partial bytes counted
            await new Promise(r => setTimeout(r, 500 * attempt));
        }
    }
}


function makeProgressTracker(totalBytes) {
    // track upload progress across all files and drives the progress bar
    const perFile = new Map();
    return {
        update(fileId, bytes) {
            perFile.set(fileId, bytes);
            let sum = 0;
            for (const v of perFile.values()) { sum += v; }
            const pct = totalBytes > 0 ? Math.min(100, Math.round((sum / totalBytes) * 100)) : 100;
            progressBar.value = pct;
            progressText.textContent = `${pretty_space(sum)} / ${pretty_space(totalBytes)}`;
        },
    };
}


async function uploadFileChunks(fileId, file, progressTracker) {
    // upload every chunk of one file in parallel
    const totalChunks = Math.ceil(file.size / uploadChunkSize);
    const chunkBytes = new Array(totalChunks).fill(0);
    let nextIndex = 0;

    function reportChunkProgress(index, loaded) {
        // update upload progress
        chunkBytes[index] = loaded;
        const uploaded = chunkBytes.reduce((a, b) => a + b, 0);
        progressTracker.update(fileId, uploaded);
    }

    async function worker() {
        // worker to send a single chunk
        while (nextIndex < totalChunks) {
            const index = nextIndex;
            nextIndex += 1;
            const start = index * uploadChunkSize;
            const end = Math.min(start + uploadChunkSize, file.size);
            const blob = file.slice(start, end);

            const result = await uploadChunkWithRetry(
                urls.uploadChunk,
                () => {
                    const fd = new FormData();
                    fd.append("file_id", fileId);
                    fd.append("chunk_index", index);
                    fd.append("chunk", blob);
                    return fd;
                },
                (loaded) => reportChunkProgress(index, loaded)
            );
            if (!result.ok) {  // failed chunk upload or write
                switch (result.error) {
                    case "missing_args":
                        throw new Error(gettext("Missing arguments while uploading chunk"));
                    case "invalid_index":
                        throw new Error(gettext("Invalid chunk index"));
                    case "nonexistent_file":
                        throw new Error(gettext("The file for this chunk does not exist"));
                    case "not_share_file":
                        throw new Error(gettext("This file is not associated with a share"));
                    case "chunk_too_large":
                        throw new Error(gettext("The uploaded chunk is too large"));
                    case "write_overflow":
                        throw new Error(gettext("Tried to write a chunk outside of the allocated size"));
                    case "write_error":
                        throw new Error(gettext("Error when trying to write a chunk"));
                    default:
                        throw new Error(gettext("Unknown chunk submission error"));
                }
            }
        }
    }

    const workerCount = Math.min(MAX_PARALLEL_CHUNKS, totalChunks) || 1;
    await Promise.all(Array.from({ length: workerCount }, worker));
}

async function runUpload() {
    // full upload sequence: start share -> per file (start -> chunks -> finish) -> finish share, returns the transfer id
    // submit form metadata first for initial validation
    const shareFd = new FormData(form);
    const shareData = await postForm(urls.startShare, shareFd);
    disableUi(true);  // now disable ui while uploading
    if (!shareData.ok) {  // failed form validation
        switch (shareData.error) {
            case "invalid_email":
                throw new Error(gettext("Invalid email address"));
            case "invalid_email_lang":
                throw new Error(gettext("Invalid email language"));
            case "invalid_delay_unit":
                throw new Error(gettext("Invalid deletion delay unit"));
            case "invalid_delay_value":
                throw new Error(gettext("Invalid deletion delay value"));
            case "invalid_path":
                throw new Error(gettext("Invalid or illegal storing path"));
            default:
                throw new Error(gettext("Unknown form validation error"));
        }
    }
    const shareId = shareData.share_id;

    const progressTracker = makeProgressTracker(totalSelectedBytes());

    // upload files one by one, chunks within a file in parallel
    for (const item of selectedFiles) {
        // initialize file upload
        const startFd = new FormData();
        startFd.append("share_id", shareId);
        startFd.append("filename", item.file.name);
        startFd.append("file_size", item.file.size);
        const fileData = await postForm(urls.startFile, startFd);
        if (!fileData.ok) {  // failed file init
            switch (fileData.error) {
                case "missing_args":
                    throw new Error(gettext("Missing arguments while initializing file upload"));
                case "nonexistant_share":
                    throw new Error(gettext("The share object does not exist"));
                case "no_space":
                    throw new Error(gettext("Not enough space to upload the file, try refreshing the storage directory to see the available space"));
                case "filename_too_long":
                    throw new Error(gettext("The file name is too long"));
                case "invalid_size":
                    throw new Error(gettext("The file size is invalid"));
                case "allocation_error":
                    throw new Error(gettext("Failed to allocate file on disk"));
                default:
                    throw new Error(gettext("Unknown file upload initialization error"));
            }
        }
        const fileId = fileData.file_id;
        
        // upload file chunk by chunk
        await uploadFileChunks(fileId, item.file, progressTracker);

        // finish file upload
        const finishFileFd = new FormData();
        finishFileFd.append("file_id", fileId);
        const result = await postForm(urls.finishFile, finishFileFd);
        if (!result.ok) {  // failed file upload finalization
            switch (result.error) {
                case "nonexistent_file":
                    throw new Error(gettext("The file for this finalization does not exist"));
                default:
                    throw new Error(gettext("Unknown file finalization error"));
            }
        }
    }

    // finish full submission
    const finishShareFd = new FormData();
    finishShareFd.append("share_id", shareId);
    const res = await postForm(urls.finishShare, finishShareFd);
    if (!res.ok) {  // failed file init
        switch (res.error) {
            case "nonexistant_share":
                throw new Error(gettext("The share object does not exist"));
            default:
                throw new Error(gettext("Unknown upload finalization error"));
        }
    }
    return shareId;
}

function disableUi(disable) {
    // disable or enable ui form
    submitBtn.disabled = disable;
    submitBtn.style.display = disable ? "none" : "";
    addBtn.disabled = disable;
    document.querySelectorAll(".remove-btn").forEach((btn) => {
        btn.disabled = disable;
    });
    document.getElementById("public").disabled = disable;
    document.getElementById("send-email").disabled = disable;
    document.getElementById("email-address").disabled = disable;
    document.getElementById("email-lang").disabled = disable;
    document.getElementById("content").disabled = disable;
    document.getElementById("expire").disabled = disable;
    document.getElementById("delay").disabled = disable;
    document.getElementById("delay-unit").disabled = disable;
    document.querySelectorAll('button[data-target="delay"]').forEach((btn) => {
        btn.disabled = disable;
    });
    document.getElementById("reset-path").disabled = disable;
    document.querySelectorAll(".path-elem").forEach((sel) => {
        sel.disabled = disable;
    });
    if (!disable) {
        // keep some stuff disabled if needed
        if (!document.getElementById("send-email").checked) {
            document.getElementById("email-address").disabled = true;
            document.getElementById("email-lang").disabled = true;
        }
        if (!document.getElementById("expire").checked) {
            document.getElementById("delay").disabled = true;
            document.getElementById("delay-unit").disabled = true;
            document.querySelectorAll('button[data-target="delay"]').forEach((btn) => {
                btn.disabled = true;
            });
        }
    }
}

form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    errorbold.textContent = "";
    error.style.display = "none";
    errorbr.style.display = "none";

    // need at least one file
    if (selectedFiles.length == 0) {
        showError(gettext("You need to upload at least one file."));
        return;
    }

    // client-side total size check before upload
    const totalBytes = totalSelectedBytes();
    if (totalBytes > max_total_bytes) {
        let total_pretty = pretty_space(totalBytes);
        let max_pretty = pretty_space(max_total_bytes);
        showError(interpolate(gettext("The uploaded files are too large. The available space is %(max_pretty)s, you tried to upload %(total_pretty)s."),
                               {max_pretty: max_pretty, total_pretty: total_pretty}, true));
        return;
    }

    // disable some ui now
    submitBtn.disabled = true;
    addBtn.disabled = true;

    progressWrap.style.display = "";
    progressBar.value = 0;
    progressText.textContent = `0B / ${pretty_space(totalBytes)}`;

    try {
        transfer_id = await runUpload();
        progressText.textContent = gettext("Done!");
        redirect_url = `${urls.endDest}?success=share_cre&transfer_id=${transfer_id}`;
        window.location.href = redirect_url;
    } catch (err) {
        showError(gettext("Upload failed: ") + String(err.message || err));
        disableUi(false);
    }
});

// Initial render
renderList();

const path_selector = document.getElementById("path-selector");  // div containing the selectors only
const info_tag = document.getElementById("path-info");  // tag to display info about path actions
const next_dirs_url = path_selector.getAttribute("data-next-dirs-url");
const reset_path_button = document.getElementById("reset-path");
const default_dir_breakdown_url = path_selector.getAttribute("data-default-dir-breakdown-url");

var path_selects = [document.getElementById("root-path")];  // array of the selects in the path selector


// make the select tag width fit the selection
function fit_select(select) {
    const measuring_span = document.createElement("span");
    measuring_span.style.cssText = `
        position: absolute;
        visibility: hidden;
        white-space: nowrap;
        font: ${getComputedStyle(select).font};
    `;
    measuring_span.textContent = select.options[select.selectedIndex].text;
    document.body.appendChild(measuring_span);
    select.style.width = (measuring_span.offsetWidth + 40) + "px";
    document.body.removeChild(measuring_span);
}

// get the full path so far, ending at last_index included
function get_full_path(last_index) {
    var full_path = "";
    for (var i=0; i<=last_index; i++) {
        full_path += path_selects[i].value;
    }
    return full_path;
}

// enable/disable each input from an array
function set_enabled(elems, enable) {
    elems.forEach(function(elem) {elem.disabled=!enable;});
}

// handle selection of a new path from one of the selects
async function update_dirs() {
    set_enabled(path_selects, false);  // disable selects while processing
    info_tag.textContent = gettext("Loading...");
    fit_select(this);
    const index = parseInt(this.getAttribute("index"));  // index of the triggered select

    // remove all the selects that come after, from the array and the page
    const to_remove = path_selects.splice(index+1);
    to_remove.forEach(function(elem) {path_selector.removeChild(elem);});

    if (this.value === ".") {  // if it's just the current dir, stop there
        info_tag.textContent = "";
        set_enabled(path_selects, true);  // re-enable selects after operations
        return;
    }

    const url = new URL(next_dirs_url, window.location.origin);
    url.searchParams.set("path", get_full_path(index));

    try {
        const response = await fetch(url);
        if (!response.ok) {
            info_tag.textContent = gettext("Request error: HTTP") + response.status;
        } else {
            const response_json = await response.json();
            if (response_json.dirs.length > 0) {
                // create and add the new select
                const new_select = document.createElement("select");
                path_selects.push(new_select);
                new_select.setAttribute("class", "path-elem");
                new_select.setAttribute("name", `path-${index+1}`);
                new_select.setAttribute("index", `${index+1}`);
                path_selector.appendChild(new_select);
                // create its options
                new_select.add(new Option(".", "."));
                response_json.dirs.forEach(function (dir) {
                    new_select.add(new Option(`${dir}/`, `${dir}/`));
                });
                fit_select(new_select);
                new_select.addEventListener("change", update_dirs);
            }
            info_tag.textContent = "";
        }
    } catch (error) {
        info_tag.textContent = gettext("Network error: ") + String(error);
    }
    set_enabled(path_selects, true);  // re-enable selects after operations
}

path_selects[0].addEventListener("change", update_dirs);  // update from selected input

// set the default directory in the path selector
//TODO: optimize with caching of the select states
async function set_default_dir() {
    set_enabled(path_selects, false);  // disable selects while processing
    info_tag.textContent = gettext("Loading...");
    const breakdown_url = new URL(default_dir_breakdown_url, window.location.origin);
    try {
        const breakdown_response = await fetch(breakdown_url);
        if (!breakdown_response.ok) {
            info_tag.textContent = gettext("Request error: HTTP") + response.status;
        }
        else {
            const breakdown_json = await breakdown_response.json();
            if (breakdown_json.breakdown.length == 0) {
                info_tag.textContent = gettext("Server error: an empty path was provided");
            }
            // update selects one by one
            const breakdown = breakdown_json.breakdown;
            var okay = true;
            for (var i=0; i<breakdown.length; i++) {
                if (!Array.from(path_selects[i].options).some(option => option.value === breakdown[i])) {
                    // if the next option is not available, it's an error
                    info_tag.textContent = gettext("Path error: the default path is not accessible");
                    okay = false;
                    break;
                }
                path_selects[i].value = breakdown[i];
                await update_dirs.call(path_selects[i]);
            }
            if (okay) {info_tag.textContent = "";}
        }
    } catch (error) {
        info_tag.textContent = gettext("Network error: ") + String(error);
    }
}

reset_path_button.addEventListener("click", set_default_dir);  // reset to default path
set_default_dir();  // init with default dir

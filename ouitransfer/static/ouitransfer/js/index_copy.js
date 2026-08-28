var copy_button = document.getElementById("copy-link");
var copy_confirm = document.getElementById("copy-confirmation");

function copy_link() {
    navigator.clipboard.writeText(copy_button.innerText);
    copy_confirm.innerHTML = gettext("Link copied!");
    setTimeout(() => { copy_confirm.innerHTML = ""; }, 2000);
}

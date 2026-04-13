const send_email_checkbox = document.getElementById("send-email");
const email_inputs = document.querySelectorAll("#email-div select, #email-div input:not([type='checkbox'])");

const expire_checkbox = document.getElementById("expire");
const expire_inputs = document.querySelectorAll("#expire-div select, #expire-div button, #expire-div input:not([type='checkbox'])");

const delay_input = document.getElementById("delay");
const delay_decr = document.querySelector("#expire-div button[decr]");
const delay_incr = document.querySelector("#expire-div button[incr]");


// handle checkboxes to enable/disable inputs
function set_inputs_state(inputs, is_checked) {
    inputs.forEach(function(input) {
        input.disabled = !is_checked;
    });
}

set_inputs_state(email_inputs, send_email_checkbox.checked);
send_email_checkbox.addEventListener("change", function() {
    set_inputs_state(email_inputs, this.checked);
});

set_inputs_state(expire_inputs, expire_checkbox.checked);
expire_checkbox.addEventListener("change", function() {
    set_inputs_state(expire_inputs, this.checked);
});

// make the number input buttons increment/decrement the value
delay_decr.addEventListener("click", function() {
    delay_input.stepDown();
});

delay_incr.addEventListener("click", function() {
    delay_input.stepUp();
});

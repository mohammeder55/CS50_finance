const inputs = document.getElementsByTagName('input'),
btn = document.getElementById('submit');

document.addEventListener('keyup', (e) => {
// Iterate over the input
for (input of inputs) {
    // If the input is Empty
    if (input.value == '') {
        btn.disabled = true
        return;
    }
}
let count = parseFloat(inputs[1].value)
// Ensure shares coutn is an integer greater than 0
if (count < 1 || !Number.isInteger(count)) {
    btn.disabled = true
    return;
}
btn.disabled = false
});

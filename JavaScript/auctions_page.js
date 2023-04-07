const socket = new WebSocket('ws://' + location.host + '/websockets');

const log = (text, color) => {
    document.getElementById('log').innerHTML += `<span style="color: ${color}">${text}</span><br>`;
  };


socket.addEventListener('message', ev => {
    log('<<< ' + ev.data, 'blue');
  });

  document.getElementById('form').onsubmit = ev => {
    ev.preventDefault();
    const textField = document.getElementById('text');
    log('>>> ' + textField.value, 'red');
    socket.send(textField.value);
    textField.value = '';
  };
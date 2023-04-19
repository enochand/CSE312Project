//Web socket connection object
const socket = new WebSocket('ws://' + location.host + '/websockets');


let me;//This is my username

socket.onopen = (event) => {
  get_identity();
  };


// Renders a new chat message to the page
function addAuction(auction) {
  let chat = document.getElementById('Auctions');
  chat.innerHTML += "<b>" + JSON.stringify(auction) + "<br/>";
}



// This function gets the clients username from the server
function get_identity() 
{
    let message = {'messageType': 'identifyMe'};
    message = JSON.stringify(message);
    socket.send(message);
}


// Called whenever data is received from the server over the WebSocket connection
socket.onmessage = function (ws_message) 
{
    const message = JSON.parse(ws_message.data);
    const messageType = message.messageType
    switch (messageType) 
    {
        case 'identity':
            me = message.token;
            break;
        case 'auctionsList':
          const auctionElem = document.getElementById("Auctions");
          let auctions = message.auctions;
          
          //TESING STUFF*************************************
          console.log(typeof(auctions));
          console.log(auctions);
          //TESING STUFF^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          
          
          for (let a of auctions.values()) {
            console.log(a);
            auctionElem.innerHTML += '<br>' + JSON.stringify(a);
          }
          break;
        default:
            console.log("received an invalid WS messageType");
    }
}


function welcome() {

}

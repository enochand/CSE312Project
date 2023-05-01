//Web socket connection object
const socket = new WebSocket('ws://' + location.host + '/websockets');


let meID;//This is my ID
let myUsername;//This is my username
let activeAuctions = {};//This will hold all the auctions that are currently active
let inactiveAuctions = {};//This will hold all the auctions that have ended

socket.onopen = (event) => {
  get_identity();
  };


// This function gets the clients username from the server
function get_identity() 
{
    let message = {'messageType': 'identifyMe'};
    message = JSON.stringify(message);
    socket.send(message);
}

function getTimestampInSeconds () {
  return Math.floor(Date.now() / 1000)
}

// Called whenever data is received from the server over the WebSocket connection
socket.onmessage = function (ws_message) 
{
    const message = JSON.parse(ws_message.data);
    const messageType = message.messageType
    switch (messageType) 
    {
        case 'identity':
            meID = message.id;
            myUsername = message.username;
            console.log(`I am ${myUsername}, with id: ${meID}`);
            break;
        
        case 'auctionsList':
            let auctions = message.auctions;
            //Loop through each auction and add them to the html
            for (let a of auctions.values()) {
              appendAuction(a);//add auction to Auctions div
            }
            break;
        
        case 'updateBid':
            updateAuctionBid(message);
            break;
        
        case 'newAuction':
            a = message.auction;//grab auction dictionary
            appendAuction(a);//append it to the html
            break;
        
        case 'endAuction':
          let auctionID = message.auction;
          let winner = message.winner;
          if (winner == myUsername) 
            {
              setWinner(auctionID);
            }
          else
            {
              setLost(auctionID);
            }
          break;
        
      
        default:
            console.log("received an invalid WS messageType");
    }
}

function updateAuctionBid(updateDictionary)
{
  let auctionID = updateDictionary.auctionID;
  let newWinner = updateDictionary.username;
  let newBidPrice = updateDictionary.bid;
  
  //update highest bidder name
  let elem = document.getElementById(auctionID + "Winner");
  elem.innerHTML = newWinner;
  
  //update highest bid number
  elem = document.getElementById(auctionID + "HighestBid");
  elem.innerHTML = newBidPrice;

  return;
}

function appendAuction(auctionDictionary)
{ 
  let currentTime = getTimestampInSeconds();
  let auctionNumber = auctionDictionary.id;
  let createdBy = auctionDictionary.username;
  let imageName = auctionDictionary.image;
  let description = auctionDictionary.description;
  let timeRemaining = auctionDictionary.time - currentTime;
  let highestBid = auctionDictionary.highest_bid;
  let winningUsername = auctionDictionary.highest_bidder;
  
  //Add to list of active auctions first
  activeAuctions[auctionNumber] = timeRemaining;//I'm putting them in a object because deleting an element is easiest on object.


  //Create element and add it to the HTML
  let auction = `<br></br><br></br>\
<div class="active_auction" id="${auctionNumber}" >\
      <p>Auction Number: ${auctionNumber}</p>\
      <p>Seller: ${createdBy}</p>\
      <img class="auction_image" src="item/${imageName}"/>\
      <p>Description: ${description}</p>\
      <p id="${auctionNumber}Time">Time Remaining: ${timeRemaining}</p>\
      <label>Current Highest Bid: </label > <label id="${auctionNumber}HighestBid">${highestBid}</label> </br>
      <label>Current Winner: </label > <label id="${auctionNumber}Winner">${winningUsername}</label> </br>
      <button id="${auctionNumber}Button" value="${auctionNumber}" onclick="sendBid(this.value);">Send bid!!</button>\
      <label>Bid</label>\
      <input id="${auctionNumber}NewBid" type="number"  min="0" step="1" oninput="validity.valid||(value='')" />\
</div>\
  `;
  const acutionsDiv = document.getElementById('Auctions');
  acutionsDiv.innerHTML += auction;
  return;
}

function sendBid(auctionID)
{
  //get value from correct text box
  let bidInput = document.getElementById(auctionID+"NewBid");
  let newBid = bidInput.value;

  //Don't have to verify newBid is a number in front end.  type="number" for input, and 
  //have to verify it's a number again anyway in server side

  //clear number from screen
  bidInput.value = '';
  
  //package into messageType: bid and send
  let message = {'messageType': 'bid', 'user_id': meID,'username': myUsername, 'auctionID': auctionID, 'bid': newBid};
  message = JSON.stringify(message);
  socket.send(message);
}


function decreaseTimeRemaining() 
{
  for (let auctionID in activeAuctions) 
  {
    let timeRemaining = activeAuctions[auctionID]-1;
    activeAuctions[auctionID] = timeRemaining;//update time left in activeAuctions
    //decrase time showed by 1
    let timeP = document.getElementById(auctionID+"Time");
    timeP.innerHTML = `Time Remaining: ${timeRemaining}`;
    if (timeRemaining <= 0) //no time left
    {
      delete activeAuctions[auctionID]; //delete from active auctions
    }
  }
}

function auctionOverHelper(auctionID)
{
  inactiveAuctions[auctionID] = 10;//add to inactive auctions, and set it to still show up for 5 seconds
  //take away bid button and input field
  let elem = document.getElementById(auctionID+"Button");
  elem.remove();
  elem = document.getElementById(auctionID+"NewBid");
  elem.remove();
  //set time remaining to 0, to help with sync issues.
  if (activeAuctions[auctionID] != undefined)
  {
    delete activeAuctions[auctionID];//Delete from active auctions dict
    let timePElem = document.getElementById(auctionID+"Time");
    timePElem.innerHTML = "Time Remaining: 0";//display time remaining as 0
  }
}

function setWinner(auctionID)
{
  //remove input buttons
  auctionOverHelper(auctionID);
  //change styling
  let auctionDiv = document.getElementById(auctionID);
  auctionDiv.className = "won_auction";
}

function setLost(auctionID)
{
  //remove input buttons
  auctionOverHelper(auctionID);
  //change styling
  let auctionDiv = document.getElementById(auctionID);
  auctionDiv.className = "ending_auction";
}

function killOldAuctionsAfter10Seconds()
{
  for (let auctionID in inactiveAuctions)
  {
    let timeRemaining = inactiveAuctions[auctionID];//get how much time left to display
    timeRemaining -= 1;//decrease by 1
    inactiveAuctions[auctionID] = timeRemaining;
    if (timeRemaining <= 0) 
    {
      //remove from html page
      let auctionDiv = document.getElementById(auctionID);
      auctionDiv.remove()//This is not supported on very old browsers, but modern ones support this
      delete inactiveAuctions[auctionID]//remove so future loops don't look at this
    }
  }
}

setInterval(decreaseTimeRemaining, 1000); //call this every second
setInterval(killOldAuctionsAfter10Seconds, 1000)

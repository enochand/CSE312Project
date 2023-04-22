// Get all auctions user won
function getWonAuctions() {
    var	request	=	new	XMLHttpRequest();
     // onreadystatechange stuff below
     request.onreadystatechange	=	function(){
        if	(this.readyState	===	4	&&	this.status	===	200){
                        // console.log(this.response);
                        const auctions = JSON.parse(this.response);
                        for (let a of auctions)
                        {
                            appendAuctionWon(a, 'wonAuctions')
                        }
        }
    };
    //Open and send the request
     request.open("GET", "/find_won_auctions");
     request.send();
    }

// Get all auctions user posted
function getAllPostedAuctions() {
    var	request	=	new	XMLHttpRequest();
     // onreadystatechange stuff below
     request.onreadystatechange	=	function(){
        if	(this.readyState	===	4	&&	this.status	===	200){
                        // console.log(this.response);
                        const auctions = JSON.parse(this.response);
                        for (let a of auctions)
                        {
                            appendAuctionPosted(a, 'postedAuctions')
                        }
        }
    };
    //Open and send the request
     request.open("GET", "/find_posted_auctions");
     request.send();
    }
function getTimestampInSeconds () {
        return Math.floor(Date.now() / 1000)
      }
function appendAuctionPosted(auctionDictionary, elemID)
    { 
      let currentTime = getTimestampInSeconds();
      let auctionNumber = auctionDictionary.id;
      let createdBy = auctionDictionary.username;
      let imageName = auctionDictionary.image;
      let description = auctionDictionary.description;
      let timeRemaining = auctionDictionary.time - currentTime;
      let highestBid = auctionDictionary.highest_bid;
      let winningUsername = auctionDictionary.highest_bidder;
      
      //Create element and add it to the HTML
      let auction = `<br>\
    <div class="posted_auction" id="${auctionNumber}" >\
          <p>Auction Number: ${auctionNumber}</p>\
          <p>Seller: ${createdBy}</p>\
          <img class="auction_image" src="item/${imageName}"/>\
          <p>Description: ${description}</p>\
          <p id="${auctionNumber}Time">Time Remaining: ${timeRemaining}</p>\
          <label>Current Highest Bid: </label > <label id="${auctionNumber}HighestBid">${highestBid}</label> </br>
          <label>Current Winner: </label > <label id="${auctionNumber}Winner">${winningUsername}</label> </br>
          <button value="${auctionNumber}" onclick="sendBid(this.value);">Send bid!!</button>\
          <label>Bid</label>\
          <input id="${auctionNumber}NewBid" type="number" />\
    </div>\
      `;
      const acutionsDiv = document.getElementById(elemID);
      acutionsDiv.innerHTML += auction;
      return;
    }

function appendAuctionWon(auctionDictionary, elemID)
    { 
      let auctionNumber = auctionDictionary.id;
      let createdBy = auctionDictionary.username;
      let imageName = auctionDictionary.image;
      let description = auctionDictionary.description;
      let highestBid = auctionDictionary.highest_bid;
    
    
      //Create element and add it to the HTML
      let auction = `<br>\
    <div class="won_auction" id="${auctionNumber}" >\
          <p>Auction Number: ${auctionNumber}</p>\
          <p>Seller: ${createdBy}</p>\
          <img class="auction_image" src="item/${imageName}"/>\
          <p>Description: ${description}</p>\
          <label>You Paid: </label > <label id="${auctionNumber}HighestBid">${highestBid}</label> </br>
    </div>\
      `;
      const acutionsDiv = document.getElementById(elemID);
      acutionsDiv.innerHTML += auction;
      return;
    }

    function welcome()
    {
        getWonAuctions();
        getAllPostedAuctions();
        return;
    }
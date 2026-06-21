function startSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        alert("Your browser does not support Speech Recognition.");
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;

    recognition.start();

    recognition.onresult = (event) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript + " ";
        }
        document.getElementById("query-input").value = transcript.trim();
    };

    recognition.onerror = (event) => {
        console.error("Speech Recognition Error:", event.error);
        alert("Speech recognition failed. Please try again.");
    };

    recognition.onspeechend = () => {
        recognition.stop();
    };
}

function formatResponse(responseText) {
    responseText = responseText.replace(/\n/g, '<br>');
    responseText = responseText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    responseText = responseText.replace(/(\d+)\.\s/g, '<br><strong>$1.</strong> ');

    responseText = responseText.replace(/[-*]\s/g, '<br>• ');

    return responseText;
}

function sendQuery() {
    const queryInput = document.getElementById("query-input");
    const userQuery = queryInput.value.trim();

    if (!userQuery) return;

    queryInput.value = "";

    const chatBox = document.getElementById("chat-box");

    const userMessage = document.createElement("div");
    userMessage.classList.add("user-query");
    userMessage.innerHTML = `<strong>You:</strong> ${userQuery}`;
    chatBox.appendChild(userMessage);
    chatBox.scrollTop = chatBox.scrollHeight;

    fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userQuery })
    })
        .then(response => response.json())
        .then(() => {
            const eventSource = new EventSource(`/stream?query=${encodeURIComponent(userQuery)}`);
            const botMessageContainer = document.createElement("div");
            botMessageContainer.classList.add("bot-response");
            chatBox.appendChild(botMessageContainer);

            let fullResponseText = '';

            eventSource.onmessage = function (event) {
                const responseChunk = event.data;
                if (responseChunk === "[DONE]") {
                    eventSource.close();
                    return;
                }
                fullResponseText += responseChunk;
                botMessageContainer.innerHTML = `<strong>Bot:</strong><br>${formatResponse(fullResponseText)}`;
                chatBox.scrollTop = chatBox.scrollHeight;
            };

            eventSource.onerror = function (error) {
                console.error("Error:", error);
                eventSource.close();
            };
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

function sendImage(event) {
    const inputElement = event.target;
    if (!inputElement || !inputElement.files || inputElement.files.length === 0) {
        console.error("No file selected or event.target is not accessible.");
        return;
    }

    const file = inputElement.files[0];
    const formData = new FormData();
    formData.append("image", file);

    const chatBox = document.getElementById("chat-box");

    const userMessage = document.createElement("div");
    userMessage.classList.add("user-query");
    userMessage.innerHTML = `<strong>You:</strong> <img src="${URL.createObjectURL(file)}" alt="Image" class="uploaded-image">`;
    chatBox.appendChild(userMessage);
    chatBox.scrollTop = chatBox.scrollHeight;

    const loadingMessage = document.createElement("div");
    loadingMessage.classList.add("bot-response");
    loadingMessage.innerHTML = `<strong>Bot:</strong> Analyzing image... <div class="loader"></div>`;
    chatBox.appendChild(loadingMessage);
    chatBox.scrollTop = chatBox.scrollHeight;

    setTimeout(() => {
        fetch('/image-query', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                chatBox.removeChild(loadingMessage);

                const botMessageContainer = document.createElement("div");
                botMessageContainer.classList.add("bot-response");

                const formattedResponse = `
                    <strong>Plant:</strong> ${data.Plant || "N/A"}<br>
                    <strong>Disease:</strong> ${data.Disease || "N/A"}<br>
                    <strong>Description:</strong> <p>${data.Description || "No description available."}</p>
                    <strong>Possible Steps:</strong> <ul>${data["Possible Steps"].split('\n').map(step => `<li>${step}</li>`).join('')}</ul>
                `;

                simulateTypingEffect(botMessageContainer, formattedResponse);
                chatBox.appendChild(botMessageContainer);
                chatBox.scrollTop = chatBox.scrollHeight;
            })
            .catch(error => {
                console.error("Error:", error);
                chatBox.removeChild(loadingMessage);
            });
    }, 1500);
}

function simulateTypingEffect(container, text) {
    let index = 0;
    const typingSpeed = 9;

    function type() {
        if (index < text.length) {
            container.innerHTML = `<strong>Bot:</strong><br>${text.substring(0, index + 1)}`;
            index++;
            setTimeout(type, typingSpeed);
        }
    }

    type();
}

document.getElementById("image-upload").addEventListener("change", sendImage);

document.addEventListener("DOMContentLoaded", function () {
    const queryInput = document.getElementById("query-input");
    const micBtn = document.getElementById("mic-btn");

    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();

        recognition.lang = "en-US";
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        micBtn.addEventListener("click", function () {
            recognition.start();
            micBtn.classList.add("listening");
        });

        recognition.onresult = function (event) {
            let transcript = "";
            for (let i = 0; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript + " ";
            }
            queryInput.value = transcript.trim();
        };

        recognition.onspeechend = function () {
            recognition.stop();
            micBtn.classList.remove("listening");
        };

        recognition.onerror = function (event) {
            console.error("Speech recognition error:", event.error);
            micBtn.classList.remove("listening");

            if (event.error === 'network') {
                alert("Network error: Please check your internet connection and try again.");
            } else if (event.error === 'no-speech') {
                alert("No speech detected. Please speak again or type your query manually.");
            } else if (event.error === 'audio-capture') {
                alert("Microphone access denied. Please allow microphone access and try again.");
            } else {
                alert("Speech recognition failed. Please try again.");
            }
        };
    } else {
        micBtn.disabled = true;
        console.error("Speech Recognition API is not supported in this browser.");
    }
});


// Theme Switch Functionality
document.addEventListener("DOMContentLoaded", function () {
    const themeSwitch = document.getElementById("theme-switch");
    const body = document.body;

    // Check for saved theme in localStorage
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) {
        body.classList.add(savedTheme);
        themeSwitch.innerHTML = savedTheme === "light-theme" ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    }

    themeSwitch.addEventListener("click", function () {
        if (body.classList.contains("light-theme")) {
            body.classList.remove("light-theme");
            localStorage.setItem("theme", "");
            themeSwitch.innerHTML = '<i class="fas fa-moon"></i>';
        } else {
            body.classList.add("light-theme");
            localStorage.setItem("theme", "light-theme");
            themeSwitch.innerHTML = '<i class="fas fa-sun"></i>';
        }
    });
});















/* General Styling */
body {
   font-family: 'Roboto', sans-serif;
   background-color: #181818; /* Dark background */
   color: #e1e1e1; /* Light text */
   display: flex;
   justify-content: center;
   align-items: center;
   flex-direction: column;
   min-height: 100vh;
   margin: 0;
   padding: 20px;
   transition: background-color 0.3s ease, color 0.3s ease;
}

body.light-theme {
   background-color: #f5f5f5; /* Light background */
   color: #333; /* Dark text */
}

/* Header Styling */
.header {
   display: flex;
   align-items: center;
   justify-content: center;
   padding: 15px 25px;
   margin-bottom: 30px;
   background-color: #20232a; /* Darker header */
   color: #e1e1e1; /* Light text */
   width: auto;
   box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3); /* Subtle shadow */
   border-radius: 50px; /* Fully rounded corners */
   transition: background-color 0.3s ease, color 0.3s ease;
}

.light-theme .header {
   background-color: #ffffff; /* Light header */
   color: #333; /* Dark text */
}

.header h1 {
   font-size: 1.8em;
   font-weight: 500;
   margin-left: 15px;
   color: inherit; /* Inherit from parent */
}

/* Logo Styling */
.logo {
   width: 60px;
   height: 60px;
   border-radius: 50%;
   object-fit: cover;
}

/* Chat Container Styling */
.chat-container {
   max-width: 800px;
   width: 100%;
   background-color: #2a2a2a; /* Dark background for chat container */
   border-radius: 12px;
   box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5); /* Darker shadow */
   overflow: hidden;
   transition: background-color 0.3s ease;
}

.light-theme .chat-container {
   background-color: #ffffff; /* Light background for chat container */
   box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); /* Lighter shadow */
}

/* Chat Box */
.chat-box {
   padding: 20px;
   height: 450px;
   overflow-y: auto;
   border-bottom: 2px solid #333; /* Dark border between messages */
   background-color: #333; /* Dark background for the chat area */
   transition: background-color 0.3s ease, border-color 0.3s ease;
}

.light-theme .chat-box {
   background-color: #f9f9f9; /* Light background for chat area */
   border-bottom-color: #ddd; /* Light border */
}

/* Chat Message Styling */
.user-query,
.bot-response {
   margin-bottom: 20px;
   padding: 15px;
   border-radius: 10px;
   line-height: 1.6;
   transition: background-color 0.3s ease, color 0.3s ease;
}

.user-query {
   background-color: #3c3c3c; /* Slightly lighter dark background for user query */
   color: #b8d9f3; /* Light text for user queries */
   text-align: right;
}

.light-theme .user-query {
   background-color: #e0e0e0; /* Light background for user query */
   color: #333; /* Dark text */
}

.bot-response {
   background-color: #484848; /* Slightly lighter dark background for bot responses */
   color: #a8dba8; /* Light green text for bot responses */
   text-align: left;
}

.light-theme .bot-response {
   background-color: #f0f0f0; /* Light background for bot responses */
   color: #2e7d32; /* Dark green text */
}

/* Input & Button Container */
.query-form {
   display: flex;
   justify-content: center;
   padding: 15px 20px;
   border-top: 2px solid #333; /* Dark top border */
   background-color: #20232a; /* Dark background for input area */
   transition: background-color 0.3s ease, border-color 0.3s ease;
}

.light-theme .query-form {
   background-color: #ffffff; /* Light background for input area */
   border-top-color: #ddd; /* Light border */
}

/* Input Field Styling */
#query-input {
   flex: 1;
   padding: 12px;
   border-radius: 25px;
   border: 1px solid #444; /* Darker border for input */
   font-size: 1.1em;
   margin-right: 15px; /* Space between input and mic button */
   margin-left: 15px;
   outline: none;
   max-width: 550px;
   background-color: #2a2a2a; /* Dark background for input */
   color: #e1e1e1; /* Light text inside input */
   transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

.light-theme #query-input {
   background-color: #ffffff; /* Light background for input */
   border-color: #ccc; /* Light border */
   color: #333; /* Dark text */
}

#query-input:focus {
   border-color: #61dafb; /* Light blue for focus */
   box-shadow: 0 0 5px rgba(97, 218, 251, 0.3);
}

/* Button Styling */
button {
   width: 50px;
   height: 50px;
   border-radius: 50%;
   border: none;
   padding: 0;
   background-color: transparent;
   display: flex;
   justify-content: center;
   align-items: center;
   margin-left: 15px; /* Space between buttons */
   cursor: pointer;
   transition: transform 0.3s ease, background-color 0.3s ease;
}

button:hover {
   transform: scale(1.1); /* Slightly enlarge on hover */
}

button .icon {
   width: 30px;
   height: 30px;
   object-fit: cover;
   filter: invert(0); /* Invert icon color for visibility in dark mode */
   transition: filter 0.3s ease;
}

.light-theme button .icon {
   filter: invert(1); /* Invert icon color for visibility in light mode */
}

/* Specific button styling for upload, mic, and send buttons */
#upload-btn,
#mic-btn,
#send-btn {
   background-color: #CB7307; /* Accent color */
}

.light-theme #upload-btn,
.light-theme #mic-btn,
.light-theme #send-btn {
   background-color: #ff9800; /* Light theme accent color */
}

/* Theme Switch Button */
.theme-switch {
   position: absolute;
   top: 20px;
   right: 20px;
   background-color: #CB7307;
   border: none;
   cursor: pointer;
   transition: background-color 0.3s ease;
}

.light-theme .theme-switch {
   background-color: #ff9800; /* Light theme accent color */
}

.theme-switch i {
   color: #fff;
   font-size: 1.2em;
}

.loader {
   border: 4px solid #f3f3f3;
   border-top: 4px solid #CB7307;
   border-radius: 50%;
   width: 20px;
   height: 20px;
   animation: spin 1s linear infinite;
   display: inline-block;
   margin-left: 10px;
}

@keyframes spin {
   0% { transform: rotate(0deg); }
   100% { transform: rotate(360deg); }
}
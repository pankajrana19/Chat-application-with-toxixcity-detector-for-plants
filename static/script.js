document.addEventListener("DOMContentLoaded", function() {
    // Chat elements
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const voiceButton = document.getElementById('voice-button');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Image detection elements
    const imageInput = document.getElementById('image-input');
    const previewImg = document.getElementById('preview-img');
    const uploadText = document.getElementById('upload-text');
    const imageSpinner = document.getElementById('image-spinner');
    const resultCard = document.getElementById('result-card');
    
    // Webcam elements
    const captureBtn = document.getElementById('capture-btn');
    const webcamContainer = document.getElementById('webcam-container');
    const webcam = document.getElementById('webcam');
    const captureSnapshot = document.getElementById('capture-snapshot');
    const canvas = document.getElementById('canvas');
    let stream = null;
    
    let currentMessageElement = null;
    let eventSource = null;

    // ==================== WEB CAMERA FUNCTIONALITY ====================
    if (captureBtn && webcam && captureSnapshot) {
        captureBtn.addEventListener('click', async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    } 
                });
                webcam.srcObject = stream;
                webcamContainer.style.display = 'block';
                previewImg.style.display = 'none';
                resultCard.style.display = 'none';
            } catch (err) {
                console.error("Error accessing webcam:", err);
                alert("Could not access webcam. Please check permissions.");
            }
        });

        captureSnapshot.addEventListener('click', () => {
            if (!stream) return;
            
            canvas.width = webcam.videoWidth;
            canvas.height = webcam.videoHeight;
            canvas.getContext('2d').drawImage(webcam, 0, 0);
            
            canvas.toBlob(blob => {
                const file = new File([blob], "webcam-capture.jpg", { 
                    type: "image/jpeg",
                    lastModified: Date.now()
                });
                
                previewImg.src = URL.createObjectURL(blob);
                previewImg.style.display = 'block';
                webcamContainer.style.display = 'none';
                uploadText.textContent = 'Change image';
                
                stream.getTracks().forEach(track => track.stop());
                stream = null;
                
                processImageForDetection(file);
            }, 'image/jpeg', 0.95);
        });
    }

    function processImageForDetection(file) {
        resultCard.style.display = 'none';
        imageSpinner.style.display = 'block';
        
        const formData = new FormData();
        formData.append('image', file);
        
        fetch('/image-query', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            imageSpinner.style.display = 'none';
            formatDiseaseResults(data);
            resultCard.style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            imageSpinner.style.display = 'none';
            alert('Error processing image. Please try again.');
        });
    }

    // ==================== CHAT FUNCTIONALITY ====================
    // Speech recognition setup
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        
        recognition.onresult = function(event) {
            const transcript = Array.from(event.results)
                .map(result => result[0].transcript)
                .join('');
            userInput.value = transcript.trim();
        };
        
        recognition.onend = function() {
            voiceButton.classList.remove('listening');
        };
        
        voiceButton.addEventListener('click', function() {
            if (recognition) {
                try {
                    voiceButton.classList.add('listening');
                    recognition.start();
                } catch (e) {
                    console.error('Recognition error:', e);
                }
            }
        });
    } else {
        voiceButton.style.display = 'none';
    }
    
    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'user-message';
        userMessageDiv.textContent = message;
        chatMessages.appendChild(userMessageDiv);
        
        userInput.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;
        typingIndicator.style.display = 'block';
        
        if (eventSource) {
            eventSource.close();
        }
        
        currentMessageElement = document.createElement('div');
        currentMessageElement.className = 'bot-message';
        currentMessageElement.textContent = '';
        chatMessages.appendChild(currentMessageElement);
        
        fetch('/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: message })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "query received") {
                startEventStream(message);
            } else {
                typingIndicator.style.display = 'none';
                currentMessageElement.textContent = data.response || "Sorry, I couldn't process your request.";
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            typingIndicator.style.display = 'none';
            currentMessageElement.textContent = "Sorry, there was an error processing your request.";
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }
    
    function startEventStream(message) {
        eventSource = new EventSource(`/stream?query=${encodeURIComponent(message)}`);
        let responseText = '';
        
        eventSource.onmessage = function(event) {
            if (event.data === "[DONE]") {
                eventSource.close();
                eventSource = null;
                typingIndicator.style.display = 'none';
                currentMessageElement.innerHTML = formatChatResponse(responseText);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                responseText += event.data;
                currentMessageElement.textContent = responseText;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        };
        
        eventSource.onerror = function(error) {
            console.error('EventSource error:', error);
            eventSource.close();
            eventSource = null;
            typingIndicator.style.display = 'none';
            
            if (responseText) {
                currentMessageElement.innerHTML = formatChatResponse(responseText);
            } else {
                currentMessageElement.textContent = "Sorry, I couldn't generate a response. Please try again.";
            }
            
            chatMessages.scrollTop = chatMessages.scrollHeight;
        };
    }

    // ==================== EVENT LISTENERS ====================
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });

    imageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                previewImg.src = e.target.result;
                previewImg.style.display = 'block';
                uploadText.textContent = 'Change image';
                resultCard.style.display = 'none';
                
                const formData = new FormData();
                formData.append('image', file);
                imageSpinner.style.display = 'block';
                
                fetch('/image-query', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    imageSpinner.style.display = 'none';
                    formatDiseaseResults(data);
                    resultCard.style.display = 'block';
                })
                .catch(error => {
                    // console.error('Error:', error);
                    imageSpinner.style.display = 'none';
                    // alert('Error processing image. Please try again.');
                });
            };
            reader.readAsDataURL(file);
        }
    });

    // ==================== HELPER FUNCTIONS ====================
    function formatChatResponse(text) {
        if (!text) return '';
        text = text.trim();
        
        // Formatting rules (same as before)
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/(\d+)\.\s/g, '<br><strong>$1.</strong> ');
        text = text.replace(/[-*]\s/g, '<br>• ');
        
        return text;
    }

    function formatDiseaseResults(data) {
        document.getElementById('result-plant').textContent = data.Plant || 'Unknown';
        document.getElementById('result-disease').textContent = data.Disease || 'Unknown';
        
        const description = document.getElementById('result-description');
        description.textContent = data.Description || 'No description available';
        
        const treatment = document.getElementById('result-treatment');
        treatment.innerHTML = '';
        
        if (data["Possible Steps"]) {
            const steps = data["Possible Steps"].split('\n');
            if (steps.length > 1) {
                const ul = document.createElement('ul');
                steps.forEach(step => {
                    if (step.trim()) {
                        const li = document.createElement('li');
                        li.textContent = step.trim().replace(/^[•*-]\s*/, '');
                        ul.appendChild(li);
                    }
                });
                treatment.appendChild(ul);
            } else {
                treatment.textContent = data["Possible Steps"];
            }
        } else {
            treatment.textContent = 'No treatment information available';
        }
    }
});
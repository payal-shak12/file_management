function uploadFile() {
    let fileInput = document.getElementById('fileInput');
    let file = fileInput.files[0];

    if (!file) {
        alert("Please select a file to upload!");
        return;
    }

    let formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch(error => console.error('Error:', error));
}

function searchFiles() {
    let query = document.getElementById('searchInput').value;

    fetch(`/search?query=${query}`)
    .then(response => response.json())
    .then(data => {
        let fileList = document.getElementById('fileList');
        fileList.innerHTML = "";  

        if (data.files.length === 0) {
            fileList.innerHTML = "<li>No files found</li>";
        } else {
            data.files.forEach(file => {
                let listItem = document.createElement('li');
                listItem.innerHTML = `
                    <strong>${file.name}</strong> (Uploaded by: ${file.uploaded_by})
                    <a href="/download/${file.id}" download="${file.name}" class="download-btn">⬇️ Download</a>
                `;
                fileList.appendChild(listItem);
            });
        }
    })
    .catch(error => console.error('Error searching files:', error));
}

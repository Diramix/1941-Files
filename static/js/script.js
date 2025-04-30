const dropArea = document.getElementById('dropArea');
const fileInput = document.getElementById('fileInput');
const progressBar = document.getElementById('progress-bar');

dropArea.addEventListener('click', () => fileInput.click());

dropArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropArea.classList.add('dragover');
});

dropArea.addEventListener('dragleave', () => {
    dropArea.classList.remove('dragover');
});

dropArea.addEventListener('drop', (e) => {
    e.preventDefault();
    dropArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        uploadFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
        uploadFile(fileInput.files[0]);
    }
});

function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);

    xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            progressBar.style.width = percent + '%';
            progressBar.textContent = percent + '%';
        }
    };

    xhr.onload = function () {
        if (xhr.status === 200) {
            progressBar.textContent = 'Готово';
            setTimeout(() => location.reload(), 1000);
        } else {
            progressBar.textContent = 'Ошибка';
        }
    };

    xhr.onerror = function () {
        progressBar.textContent = 'Ошибка';
    };

    xhr.send(formData);
}

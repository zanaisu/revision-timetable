let curriculumData = null;

async function loadCurriculumData() {
    if (!curriculumData) {
        const response = await fetch('/static/data/curriculum.json');
        curriculumData = await response.json();
    }
    return curriculumData;
}

function toggleCurriculum() {
    const modal = document.getElementById('curriculumModal');
    if (modal.style.display !== 'block') {
        modal.style.display = 'block';
        if (!curriculumData) {
            loadCurriculumData().then(renderCurriculum);
        }
    } else {
        modal.style.display = 'none';
    }
}

function renderCurriculum(data) {
    const content = document.getElementById('curriculumContent');
    // Implement rendering logic here based on the JSON structure
    // This will create the HTML structure for displaying the curriculum
}

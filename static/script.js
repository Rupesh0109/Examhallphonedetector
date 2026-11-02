const cameraSelect = document.getElementById('cameraSelect');
const refreshCameras = document.getElementById('refreshCameras');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const selectedCamera = document.getElementById('selectedCamera');
const videoFeed = document.getElementById('videoFeed');
const alertBox = document.getElementById('alertBox');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const peopleCount = document.getElementById('peopleCount');
const phoneCount = document.getElementById('phoneCount');
const warningCount = document.getElementById('warningCount');
const incidentCount = document.getElementById('incidentCount');
const permBtn = document.getElementById('permBtn');
const browserCams = document.getElementById('browserCams');

let pollInterval = null;

async function loadCameras(){
  const res = await fetch('/cameras');
  const data = await res.json();
  cameraSelect.innerHTML = '';
  if(!data.cameras.length){
    const opt = document.createElement('option');
    opt.textContent = 'No cameras found';
    cameraSelect.appendChild(opt);
    return;
  }
  data.cameras.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.index;
    opt.textContent = c.name;
    cameraSelect.appendChild(opt);
  });
  updateSelectedName();
}

function updateSelectedName(){
  const opt = cameraSelect.options[cameraSelect.selectedIndex];
  selectedCamera.textContent = opt ? opt.textContent : 'None';
}

cameraSelect.addEventListener('change', updateSelectedName);
refreshCameras.addEventListener('click', loadCameras);

async function selectCameraOnBackend(){
  const idx = cameraSelect.value;
  const res = await fetch('/camera/select', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({index: idx})});
  const data = await res.json();
  if(!data.ok){ alert(data.error); return false; }
  return true;
}

startBtn.addEventListener('click', async () => {
  const ok = await selectCameraOnBackend();
  if(!ok) return;
  const res = await fetch('/camera/start', {method:'POST'});
  const data = await res.json();
  if(!data.ok){ alert(data.error); return; }
  videoFeed.src = '/video_feed?' + Date.now();
  statusDot.classList.add('running');
  statusText.textContent = 'Running';
  startPolling();
});

stopBtn.addEventListener('click', async () => {
  await fetch('/camera/stop', {method:'POST'});
  videoFeed.src = '';
  statusDot.classList.remove('running');
  statusText.textContent = 'Stopped';
  stopPolling();
  peopleCount.textContent = '0';
  phoneCount.textContent = '0';
  warningCount.textContent = '0';
  alertBox.textContent = 'Camera stopped.';
  alertBox.className = 'alert normal';
});

function startPolling(){
  if(pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(async () => {
    const res = await fetch('/stats');
    const data = await res.json();
    peopleCount.textContent = data.people;
    phoneCount.textContent = data.phones;
    warningCount.textContent = data.warnings;
    if(typeof data.incident_count !== 'undefined') incidentCount.textContent = data.incident_count;
    if(data.alert){
      alertBox.textContent = data.alert_message;
      alertBox.className = 'alert warning';
    } else {
      alertBox.textContent = data.alert_message || 'No phone detected near a person.';
      alertBox.className = 'alert normal';
    }
    if(!data.running){
      statusDot.classList.remove('running');
      statusText.textContent = 'Stopped';
    }
  }, 1000);
}
function stopPolling(){
  if(pollInterval){ clearInterval(pollInterval); pollInterval=null; }
}

permBtn.addEventListener('click', async () => {
  try {
    await navigator.mediaDevices.getUserMedia({video:true});
    const devices = await navigator.mediaDevices.enumerateDevices();
    const vids = devices.filter(d=>d.kind==='videoinput');
    browserCams.innerHTML = '<strong>Browser cameras:</strong><br>' + vids.map((d,i)=>`${i}: ${d.label||'Unnamed camera'}`).join('<br>');
  } catch(e){
    browserCams.textContent = 'Permission denied or unavailable: ' + e.message;
  }
});

loadCameras();
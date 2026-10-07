/**
 * Add Bill Controller (Manual Entry & OCR Upload Flow)
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!TokenManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  initTabs();
  await prefillLastReadingAndMonth();
  setupLiveCalculator();
  setupManualFormSubmit();
  setupUploadZone();
  setupOcrModal();
});

function initTabs() {
  const manualBtn = document.getElementById('tab-manual-btn');
  const uploadBtn = document.getElementById('tab-upload-btn');
  const manualContent = document.getElementById('tab-manual-content');
  const uploadContent = document.getElementById('tab-upload-content');

  manualBtn?.addEventListener('click', () => {
    manualBtn.classList.add('active');
    uploadBtn.classList.remove('active');
    manualContent.style.display = 'grid';
    uploadContent.style.display = 'none';
  });

  uploadBtn?.addEventListener('click', () => {
    uploadBtn.classList.add('active');
    manualBtn.classList.remove('active');
    uploadContent.style.display = 'block';
    manualContent.style.display = 'none';
  });
}

async function prefillLastReadingAndMonth() {
  try {
    const res = await apiFetch('/bills');
    const bills = res.data || [];
    
    // Set default month to current or next month
    const now = new Date();
    const currentMonthStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    const monthInput = document.getElementById('month');
    if (monthInput && !monthInput.value) {
      monthInput.value = currentMonthStr;
    }

    if (bills.length > 0) {
      const latest = bills[0]; // sorted descending by month
      const prevInput = document.getElementById('prev_reading');
      if (prevInput && !prevInput.value && latest.current_reading) {
        prevInput.value = latest.current_reading;
      }
    }
  } catch (err) {
    console.error('Error prefilling last reading:', err);
  }
}

function setupLiveCalculator() {
  const prevInput = document.getElementById('prev_reading');
  const currInput = document.getElementById('curr_reading');
  const unitsInput = document.getElementById('computed_units');
  const rebateInput = document.getElementById('rebate');
  const otherInput = document.getElementById('other_charges');

  let debounceTimer;

  function update() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      const prev = parseFloat(prevInput.value) || 0;
      const curr = parseFloat(currInput.value) || 0;

      if (curr >= prev && curr > 0) {
        const units = Math.max(0, curr - prev);
        unitsInput.value = units;

        const rebate = parseFloat(rebateInput.value) || 0;
        const other = parseFloat(otherInput.value) || 0;

        try {
          const calcRes = await apiFetch('/bills/calculate', {
            method: 'POST',
            body: JSON.stringify({ units, rebate, other_charges: other })
          });

          renderLivePreview(calcRes.data);
        } catch (e) {
          console.error(e);
        }
      }
    }, 200);
  }

  prevInput?.addEventListener('input', update);
  currInput?.addEventListener('input', update);
  rebateInput?.addEventListener('input', update);
  otherInput?.addEventListener('input', update);
}

function renderLivePreview(data) {
  const linesContainer = document.getElementById('preview-lines');
  const energyEl = document.getElementById('preview-energy');
  const fixedEl = document.getElementById('preview-fixed');
  const dutyEl = document.getElementById('preview-duty');
  const totalEl = document.getElementById('preview-total');

  if (!data || !linesContainer) return;

  const linesHtml = data.lines.map(l => `
    <div style="display:flex; justify-content:space-between; margin-bottom:0.25rem;">
      <span style="color:var(--text-secondary);">Slab ${l.range} (${l.units}u @ ₹${l.rate}):</span>
      <strong style="color:var(--text-primary);">₹${l.amount.toFixed(2)}</strong>
    </div>
  `).join('');

  linesContainer.innerHTML = linesHtml;
  energyEl.innerText = formatCurrency(data.energy_charge);
  fixedEl.innerText = formatCurrency(data.fixed_charge);
  dutyEl.innerText = formatCurrency(data.duty);
  totalEl.innerText = formatCurrency(data.total);

  // ── Appliance usage breakdown (manual tab) ──
  const prevVal = parseFloat(document.getElementById('prev_reading').value) || 0;
  const currVal = parseFloat(document.getElementById('curr_reading').value) || 0;
  const units = Math.max(0, currVal - prevVal);
  if (units > 0) {
    renderApplianceTiles(
      'manual-app-grid',
      units,
      data.total,
      'manual-kwh-label',
      'manual-appliance-section'
    );
  }
}

function setupManualFormSubmit() {
  const form = document.getElementById('manual-bill-form');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('save-bill-btn');
    btn.disabled = true;
    btn.innerText = 'Saving Bill...';

    const month = document.getElementById('month').value;
    const prev = parseFloat(document.getElementById('prev_reading').value);
    const curr = parseFloat(document.getElementById('curr_reading').value);
    const actual_total = document.getElementById('actual_total').value ? parseFloat(document.getElementById('actual_total').value) : null;
    const rebate = parseFloat(document.getElementById('rebate').value) || 0;
    const other = parseFloat(document.getElementById('other_charges').value) || 0;

    try {
      await apiFetch('/bills', {
        method: 'POST',
        body: JSON.stringify({
          month,
          previous_reading: prev,
          current_reading: curr,
          actual_total,
          rebate,
          other_charges: other,
          source: 'manual'
        })
      });

      showToast('Bill saved successfully!', 'success');
      setTimeout(() => {
        window.location.href = '/history.html';
      }, 700);
    } catch (err) {
      btn.disabled = false;
      btn.innerText = '💾 Save Bill to History';
    }
  });
}

function setupUploadZone() {
  const dropzone = document.getElementById('upload-dropzone');
  const fileInput = document.getElementById('file-input');
  const loading = document.getElementById('ocr-loading');

  ['dragenter', 'dragover'].forEach(name => {
    dropzone?.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropzone?.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone?.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  });

  fileInput?.addEventListener('change', (e) => {
    if (fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  async function handleFileUpload(file) {
    dropzone.style.display = 'none';
    loading.style.display = 'block';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await apiFetch('/bills/upload', {
        method: 'POST',
        body: formData
      });

      populateOcrModal(res.data);
    } catch (err) {
      dropzone.style.display = 'block';
      loading.style.display = 'none';
    }
  }
}

function populateOcrModal(data) {
  const modal = document.getElementById('ocr-modal');
  const loading = document.getElementById('ocr-loading');
  const dropzone = document.getElementById('upload-dropzone');

  loading.style.display = 'none';
  dropzone.style.display = 'block';

  document.getElementById('ocr-filename').value = data.saved_filename || '';
  document.getElementById('ocr-month').value = data.month || new Date().toISOString().slice(0, 7);
  document.getElementById('ocr-prev').value = data.previous_reading || 0;
  document.getElementById('ocr-curr').value = data.current_reading || (data.units || 0);
  document.getElementById('ocr-units').value = data.units || 0;
  document.getElementById('ocr-total').value = data.total_amount || 0;

  if (data.calculated_preview) {
    document.getElementById('ocr-calc-total').innerText = formatCurrency(data.calculated_preview.total);
  }

  // ── Appliance usage breakdown in OCR modal ──
  const units = parseFloat(data.units) || 0;
  const totalAmt = parseFloat(data.total_amount) || (data.calculated_preview ? data.calculated_preview.total : 0);
  if (units > 0) {
    renderApplianceTiles(
      'ocr-app-grid',
      units,
      totalAmt,
      'ocr-kwh-label',
      'ocr-appliance-section'
    );
  }

  modal.classList.add('show');
}

function setupOcrModal() {
  const modal = document.getElementById('ocr-modal');
  const closeBtn = document.getElementById('close-modal-btn');
  const form = document.getElementById('ocr-confirm-form');

  closeBtn?.addEventListener('click', () => {
    modal.classList.remove('show');
  });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('ocr-save-btn');
    btn.disabled = true;
    btn.innerText = 'Confirming...';

    const month = document.getElementById('ocr-month').value;
    const prev = parseFloat(document.getElementById('ocr-prev').value);
    const curr = parseFloat(document.getElementById('ocr-curr').value);
    const units = parseFloat(document.getElementById('ocr-units').value);
    const actual_total = parseFloat(document.getElementById('ocr-total').value);
    const file_name = document.getElementById('ocr-filename').value;

    try {
      await apiFetch('/bills', {
        method: 'POST',
        body: JSON.stringify({
          month,
          previous_reading: prev,
          current_reading: curr,
          units,
          actual_total,
          source: 'upload',
          file_name
        })
      });

      modal.classList.remove('show');
      showToast('Bill verified & saved successfully!', 'success');
      setTimeout(() => {
        window.location.href = '/history.html';
      }, 700);
    } catch (err) {
      btn.disabled = false;
      btn.innerText = '✅ Confirm & Save Bill';
    }
  });
}

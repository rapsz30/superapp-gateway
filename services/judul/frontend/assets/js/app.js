/**
 * ============================================
 * CHATBOT REKOMENDASI TA - MAIN APPLICATION
 * ============================================
 * Author: [Hafidh Rahman]
 * Date: December 2025
 * Description: Handles form submission, API calls, and UI updates
 */

// ============================================
// 1. CONFIGURATION & CONSTANTS
// ============================================

const CONFIG = {
  // Backend API URL
  API_BASE_URL: 'http://localhost:8001',

  // API Endpoints
  ENDPOINTS: {
    recommendations: '/get-recommendations',
  },

  // Request timeout (milliseconds)
  TIMEOUT: 120000, // 2 minutes (karena AI bisa lambat)
};

// ============================================
// 2. DOM ELEMENTS
// ============================================

// Form elements
const form = document.getElementById('recommendationForm');
const interestsInput = document.getElementById('interestsInput');
const submitBtn = document.getElementById('submitBtn');

// Section elements
const loadingSection = document.getElementById('loadingSection');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('resultsSection');
const recommendationsGrid = document.getElementById('recommendationsGrid');

// Action buttons
const exportPdfBtn = document.getElementById('exportPdfBtn');
const printBtn = document.getElementById('printBtn');

// Suggestion pills
const suggestionPills = document.querySelectorAll('.pill-btn');

// ============================================
// 3. STATE MANAGEMENT
// ============================================

/**
 * Application state
 * Menyimpan data yang sedang diproses
 */
let appState = {
  isLoading: false,
  currentRecommendations: null,
  currentQuery: '',
};

// ============================================
// 4. EVENT LISTENERS
// ============================================

/**
 * Initialize all event listeners
 * Dipanggil saat page load
 */
function initializeEventListeners() {
  // Form submission
  form.addEventListener('submit', handleFormSubmit);

  // Suggestion pills click
  suggestionPills.forEach((pill) => {
    pill.addEventListener('click', handleSuggestionClick);
  });

  // Export PDF button
  exportPdfBtn.addEventListener('click', handleExportPdf);

  // Print button
  printBtn.addEventListener('click', handlePrint);
}

// ============================================
// 5. FORM HANDLING
// ============================================

/**
 * Handle form submission
 * @param {Event} event - Form submit event
 */
async function handleFormSubmit(event) {
  // Prevent default form submission (yang akan reload page)
  event.preventDefault();

  // Get user input
  const interests = interestsInput.value.trim();

  // Validation: Check if input is empty
  if (!interests) {
    showError('Mohon masukkan topik yang ingin Anda eksplorasi.');
    return;
  }

  // Save query to state
  appState.currentQuery = interests;

  // Call API untuk get recommendations
  await getRecommendations(interests);
}

/**
 * Handle suggestion pill click
 * Auto-fill input dengan suggestion
 */
function handleSuggestionClick(event) {
  const suggestion = event.currentTarget.dataset.suggestion;
  interestsInput.value = suggestion;
  interestsInput.focus();
}

// ============================================
// 6. API CALLS
// ============================================

/**
 * Get recommendations dari backend API
 * @param {string} interests - User's interests/topic
 */
async function getRecommendations(interests) {
  try {
    // Show loading state
    showLoading();

    // Prepare request data
    const requestData = {
      interests: interests,
    };

    console.log('Sending request to API:', CONFIG.API_BASE_URL + CONFIG.ENDPOINTS.recommendations);
    console.log('Request data:', requestData);

    // Make API call dengan timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.TIMEOUT);

    const response = await fetch(CONFIG.API_BASE_URL + CONFIG.ENDPOINTS.recommendations, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Check if response is OK
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    // Parse JSON response
    const data = await response.json();

    console.log('Received response:', data);

    // Validate response structure
    if (!data.rekomendasi || !Array.isArray(data.rekomendasi)) {
      throw new Error('Format response tidak valid dari server');
    }

    // Save to state
    appState.currentRecommendations = data;

    // Display results
    displayRecommendations(data.rekomendasi);
  } catch (error) {
    console.error('Error getting recommendations:', error);

    // Handle different error types
    if (error.name === 'AbortError') {
      showError('Request timeout. Server membutuhkan waktu terlalu lama. Silakan coba lagi.');
    } else if (error.message.includes('Failed to fetch')) {
      showError('Tidak dapat terhubung ke server. Pastikan backend sedang berjalan di ' + CONFIG.API_BASE_URL);
    } else {
      showError('Terjadi kesalahan: ' + error.message);
    }
  } finally {
    // Hide loading state
    hideLoading();
  }
}

// ============================================
// 7. UI STATE MANAGEMENT
// ============================================

/**
 * Show loading state
 * Hide other sections, show loading animation
 */
function showLoading() {
  appState.isLoading = true;

  // Disable submit button
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Memproses...';

  // Hide other sections
  hideError();
  hideResults();

  // Show loading section
  loadingSection.style.display = 'block';

  // Smooth scroll to loading section
  loadingSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Hide loading state
 */
function hideLoading() {
  appState.isLoading = false;

  // Enable submit button
  submitBtn.disabled = false;
  submitBtn.innerHTML = '<i class="bi bi-send-fill"></i><span>Cari Rekomendasi</span>';

  // Hide loading section
  loadingSection.style.display = 'none';
}

/**
 * Show error message
 * @param {string} message - Error message to display
 */
function showError(message) {
  errorMessage.textContent = message;
  errorSection.style.display = 'block';

  // Smooth scroll to error
  errorSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Hide error message
 */
function hideError() {
  errorSection.style.display = 'none';
}

/**
 * Show results section
 */
function showResults() {
  resultsSection.style.display = 'block';

  // Smooth scroll to results
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Hide results section
 */
function hideResults() {
  resultsSection.style.display = 'none';
}

// ============================================
// 8. DISPLAY RECOMMENDATIONS
// ============================================

/**
 * Display recommendations in cards
 * @param {Array} recommendations - Array of recommendation objects
 */
function displayRecommendations(recommendations) {
  // Clear previous results
  recommendationsGrid.innerHTML = '';

  // Check if we have recommendations
  if (!recommendations || recommendations.length === 0) {
    showError('Tidak ada rekomendasi yang ditemukan. Silakan coba dengan topik lain.');
    return;
  }

  // Create card untuk setiap recommendation
  recommendations.forEach((rec, index) => {
    const card = createRecommendationCard(rec, index + 1);
    recommendationsGrid.appendChild(card);
  });

  // Show results section
  showResults();
}

/**
 * Create recommendation card element
 * @param {Object} recommendation - Recommendation data
 * @param {number} number - Card number (1, 2, 3)
 * @returns {HTMLElement} Card element
 */
function createRecommendationCard(recommendation, number) {
  // Create column div (Bootstrap grid)
  const col = document.createElement('div');
  col.className = 'col-12 col-md-6 col-lg-4'; // Responsive columns

  // Create card HTML
  col.innerHTML = `
        <div class="recommendation-card">
            <!-- Card Header -->
            <div class="card-header-custom">
                <div class="card-number">${number}</div>
            </div>
            
            <!-- Judul -->
            <h3 class="card-title-custom">
                ${escapeHtml(recommendation.judul || 'Tidak ada judul')}
            </h3>
            
            <!-- Deskripsi -->
            <div class="card-section">
                <div class="section-title">
                    <i class="bi bi-file-text"></i>
                    Deskripsi
                </div>
                <div class="section-content">
                    ${escapeHtml(recommendation.deskripsi || 'Tidak ada deskripsi')}
                </div>
            </div>
            
            <!-- Metodologi -->
            <div class="card-section">
                <div class="section-title">
                    <i class="bi bi-diagram-3"></i>
                    Metodologi
                </div>
                <div class="section-content">
                    ${formatMethodology(recommendation.metodologi)}
                </div>
            </div>
            
            <!-- Keywords -->
            ${
              recommendation.keywords && recommendation.keywords.length > 0
                ? `
                <div class="card-section">
                    <div class="section-title">
                        <i class="bi bi-tags"></i>
                        Keywords
                    </div>
                    <div class="keywords-container">
                        ${recommendation.keywords.map((kw) => `<span class="keyword-tag">${escapeHtml(kw)}</span>`).join('')}
                    </div>
                </div>
            `
                : ''
            }
            
            <!-- Referensi -->
            ${
              recommendation.referensi && recommendation.referensi.length > 0
                ? `
                <div class="card-section">
                    <div class="section-title">
                        <i class="bi bi-journal-text"></i>
                        Referensi Akademik
                    </div>
                    <ul class="references-list">
                        ${recommendation.referensi.map((ref) => createReferenceItem(ref)).join('')}
                    </ul>
                </div>
            `
                : ''
            }
        </div>
    `;

  return col;
}

/**
 * Create reference list item
 * @param {Object} reference - Reference object
 * @returns {string} HTML string
 */
function createReferenceItem(reference) {
  return `
        <li class="reference-item">
            <div class="reference-text">${escapeHtml(reference.sitasi || 'Tidak ada sitasi')}</div>
            ${
              reference.link
                ? `
                <a href="${escapeHtml(reference.link)}" 
                   target="_blank" 
                   rel="noopener noreferrer" 
                   class="reference-link">
                    <i class="bi bi-link-45deg"></i>
                    Akses Paper
                </a>
            `
                : ''
            }
        </li>
    `;
}

/**
 * Format methodology text dengan line breaks
 * @param {string} methodology - Methodology text
 * @returns {string} Formatted HTML
 */
function formatMethodology(methodology) {
  if (!methodology) return 'Tidak ada metodologi';

  // Handle kalau metodologi adalah object (structured format dari AI)
  if (typeof methodology === 'object' && !Array.isArray(methodology)) {
    let formatted = '';

    // Loop setiap tahap
    Object.entries(methodology).forEach(([tahap, detail], index) => {
      formatted += `
                <div class="methodology-step">
                    <strong class="step-title">${tahap}</strong>
                    <div class="step-detail">${detail}</div>
                </div>
            `;
    });

    return formatted;
  }

  // Handle kalau string biasa
  if (typeof methodology !== 'string') {
    methodology = String(methodology);
  }

  // Format string dengan line breaks
  return methodology.replace(/\n/g, '<br>').replace(/(\d+\.)/g, '<strong>$1</strong>');
}

/**
 * Escape HTML untuk prevent XSS
 * Security: Prevent malicious code injection
 * @param {string} unsafe - Unsafe string
 * @returns {string} Safe HTML string
 */
function escapeHtml(unsafe) {
  // Handle null, undefined, atau non-string
  if (unsafe === null || unsafe === undefined) {
    return '';
  }

  // Convert to string kalau bukan string
  if (typeof unsafe !== 'string') {
    unsafe = String(unsafe);
  }

  return unsafe.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

// ============================================
// 9. EXPORT & PRINT FUNCTIONS
// ============================================

/**
 * Handle Export to PDF
 * Note: Ini placeholder - butuh library seperti jsPDF
 */
function handleExportPdf() {
  if (!appState.currentRecommendations) {
    alert('Tidak ada data untuk di-export');
    return;
  }

  // TODO: Implement PDF export
  // Untuk sekarang, kasih alert
  alert('Fitur export PDF akan diimplementasikan di step selanjutnya!\n\nUntuk sekarang, gunakan Print untuk save sebagai PDF.');

  // Alternative: Use print dialog dengan save as PDF
  window.print();
}

/**
 * Handle Print
 * Uses browser's print dialog
 */
function handlePrint() {
  if (!appState.currentRecommendations) {
    alert('Tidak ada data untuk di-print');
    return;
  }

  // Use browser's print function
  window.print();
}

// ============================================
// 10. INITIALIZATION
// ============================================

/**
 * Initialize application
 * Dipanggil saat page load
 */
function init() {
  console.log('Initializing Chatbot Rekomendasi TA...');
  console.log('Backend URL:', CONFIG.API_BASE_URL);

  // Setup event listeners
  initializeEventListeners();

  // Focus pada input field
  interestsInput.focus();

  console.log('Application ready!');
}

// Run initialization saat DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

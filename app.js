/**
 * app.js - Bespoke Math Flashcard Application
 * Handles views, deck shuffling, 3D card flips, KaTeX mathematical typesetting,
 * mobile touch gestures, and keyboard navigation.
 */

(function () {
  'use strict';

  // KaTeX custom macro mapping (matching LaTeX preambles)
  const KATEX_MACROS = {
    "\\C": "\\mathbb{C}",
    "\\R": "\\mathbb{R}",
    "\\N": "\\mathbb{N}",
    "\\Z": "\\mathbb{Z}",
    "\\Q": "\\mathbb{Q}",
    "\\id": "\\operatorname{id}",
    "\\mod": "\\ (\\operatorname{mod} #1)",
    "\\cyc": "\\langle #1 \\rangle",
    "\\ip": "\\langle #1 \\rangle",
    "\\intr": "\\operatorname{int}",
    "\\dom": "\\operatorname{dom}",
    "\\inc": "\\text{\\footnotesize\\phantom{.}I\\phantom{.}}",
    "\\rbracket": "]",
    "\\abs": "\\left|#1\\right|",
    "\\norm": "\\left\\|#1\\right\\|",
    "\\slash": "/",
    "\\emph": "\\textcolor{red}{#1}"
  };

  // Application State
  const state = {
    courses: [],
    currentCourse: null,
    selectedChapters: new Set(),
    deck: [],
    currentIndex: 0,
    isFlipped: false,
    currentView: 'landing' // 'landing' | 'chapters' | 'study' | 'complete'
  };

  // DOM Elements
  const elements = {
    viewLanding: document.getElementById('view-landing'),
    viewChapters: document.getElementById('view-chapters'),
    viewStudy: document.getElementById('view-study'),
    viewComplete: document.getElementById('view-complete'),
    
    courseGrid: document.getElementById('course-grid'),
    
    chapterCourseTitle: document.getElementById('chapter-course-title'),
    chapterCourseBadge: document.getElementById('chapter-course-badge'),
    chapterGrid: document.getElementById('chapter-grid'),
    btnSelectAllChapters: document.getElementById('btn-select-all'),
    btnClearAllChapters: document.getElementById('btn-clear-all'),
    btnStartStudying: document.getElementById('btn-start-studying'),
    selectedCountBadge: document.getElementById('selected-count-badge'),
    btnBackToCourses: document.getElementById('btn-back-to-courses'),
    
    btnExitStudy: document.getElementById('btn-exit-study'),
    btnShuffleDeck: document.getElementById('btn-shuffle-deck'),
    studyCardCounter: document.getElementById('study-card-counter'),
    studyChapterBadge: document.getElementById('study-chapter-badge'),
    studyProgressBar: document.getElementById('study-progress-bar'),
    
    flashcard: document.getElementById('flashcard'),
    cardTerm: document.getElementById('card-term'),
    cardDefinition: document.getElementById('card-definition'),
    cardSectionLabel: document.getElementById('card-section-label'),
    cardChLabel: document.getElementById('card-ch-label'),
    
    btnFlipCard: document.getElementById('btn-flip-card'),
    btnNextCard: document.getElementById('btn-next-card'),
    btnPrevCard: document.getElementById('btn-prev-card'),
    
    completeCourseTitle: document.getElementById('complete-course-title'),
    completeSummaryText: document.getElementById('complete-summary-text'),
    completeTotalCards: document.getElementById('complete-total-cards'),
    completeTotalChapters: document.getElementById('complete-total-chapters'),
    btnRestartSession: document.getElementById('btn-restart-session'),
    btnBackToChapterSelect: document.getElementById('btn-back-to-chapter-select'),
    btnBackToMainMenu: document.getElementById('btn-back-to-main-menu')
  };

  /**
   * Helper: Fisher-Yates array shuffle
   */
  function shuffleArray(array) {
    const copy = [...array];
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  /**
   * Render math within an element using KaTeX auto-render
   */
  function renderMath(element) {
    if (!element) return;
    if (typeof renderMathInElement === 'function') {
      try {
        renderMathInElement(element, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '\\[', right: '\\]', display: true },
            { left: '$', right: '$', display: false },
            { left: '\\(', right: '\\)', display: false }
          ],
          macros: KATEX_MACROS,
          throwOnError: false
        });
      } catch (err) {
        console.warn('KaTeX rendering warning:', err);
      }
    }
  }

  /**
   * Switch active view with smooth animation
   */
  function setView(viewName) {
    state.currentView = viewName;
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (viewName === 'landing') {
      elements.viewLanding.classList.add('active');
    } else if (viewName === 'chapters') {
      elements.viewChapters.classList.add('active');
    } else if (viewName === 'study') {
      elements.viewStudy.classList.add('active');
    } else if (viewName === 'complete') {
      elements.viewComplete.classList.add('active');
    }
  }

  /**
   * Initialize Course Selection Landing Page
   */
  function renderCourseLanding() {
    elements.courseGrid.innerHTML = '';
    
    state.courses.forEach(course => {
      const card = document.createElement('div');
      card.className = 'course-card';
      
      const badgeClass = course.code.includes('301') ? 'badge-301' : 
                         course.code.includes('410') ? 'badge-410' : 'badge-461';

      card.innerHTML = `
        <div>
          <span class="course-badge ${badgeClass}">${course.code}</span>
          <h3 class="course-title">${course.title}</h3>
          <p class="course-textbook">${course.textbook}</p>
        </div>
        <div class="course-meta">
          <span><strong>${course.chapters.length}</strong> Chapters</span>
          <span><strong>${course.totalTerms}</strong> Definitions</span>
        </div>
      `;

      card.addEventListener('click', () => {
        selectCourse(course);
      });

      elements.courseGrid.appendChild(card);
    });
  }

  /**
   * User selects a course -> navigate to Chapter Selection
   */
  function selectCourse(course) {
    state.currentCourse = course;
    elements.chapterCourseTitle.textContent = `${course.code}: ${course.title}`;
    elements.chapterCourseBadge.textContent = course.code;
    
    // Default: nothing selected per user directive
    state.selectedChapters = new Set();
    
    renderChapterSelection();
    setView('chapters');
  }

  /**
   * Render Chapter selection list with checkboxes & counts
   */
  function renderChapterSelection() {
    if (!state.currentCourse) return;
    elements.chapterGrid.innerHTML = '';

    state.currentCourse.chapters.forEach(ch => {
      const isSelected = state.selectedChapters.has(ch.name);
      
      const card = document.createElement('div');
      card.className = `chapter-card ${isSelected ? 'selected' : ''}`;
      
      card.innerHTML = `
        <div class="chapter-checkbox">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
        <div class="chapter-info">
          <h3>${ch.name}</h3>
          <p>${ch.count} ${ch.count === 1 ? 'definition' : 'definitions'}</p>
        </div>
      `;

      card.addEventListener('click', () => {
        if (state.selectedChapters.has(ch.name)) {
          state.selectedChapters.delete(ch.name);
        } else {
          state.selectedChapters.add(ch.name);
        }
        renderChapterSelection();
      });

      elements.chapterGrid.appendChild(card);
    });

    updateSelectionSummary();
  }

  /**
   * Update Chapter selection count badge and enable/disable start button
   */
  function updateSelectionSummary() {
    if (!state.currentCourse) return;
    
    let totalCards = 0;
    state.currentCourse.chapters.forEach(ch => {
      if (state.selectedChapters.has(ch.name)) {
        totalCards += ch.count;
      }
    });

    elements.selectedCountBadge.innerHTML = `<strong>${totalCards}</strong> definitions selected`;
    elements.btnStartStudying.disabled = totalCards === 0;
    if (totalCards === 0) {
      elements.btnStartStudying.innerHTML = `Select Chapters to Start`;
    } else {
      elements.btnStartStudying.innerHTML = `Start Studying (${totalCards}) <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>`;
    }
  }

  /**
   * Start study session with selected chapters
   */
  function startStudySession() {
    if (!state.currentCourse || state.selectedChapters.size === 0) return;

    // Filter cards belonging to selected chapters
    const eligibleCards = state.currentCourse.cards.filter(c => state.selectedChapters.has(c.chapter));
    if (eligibleCards.length === 0) return;

    // Shuffle cards
    state.deck = shuffleArray(eligibleCards);
    state.currentIndex = 0;
    state.isFlipped = false;

    renderCurrentCard();
    setView('study');
  }

  /**
   * Render the active card and update study controls
   */
  function renderCurrentCard() {
    if (!state.deck.length) return;
    const card = state.deck[state.currentIndex];

    // Reset flip orientation
    state.isFlipped = false;
    elements.flashcard.classList.remove('flipped');
    elements.btnFlipCard.innerHTML = `<span>Flip Card</span> <span class="kbd-hint">Space</span>`;

    // Update Header stats
    const currentNum = state.currentIndex + 1;
    const totalNum = state.deck.length;
    elements.studyCardCounter.innerHTML = `Card <strong>${currentNum}</strong> of ${totalNum}`;
    elements.studyChapterBadge.textContent = card.section ? `${card.chapter} (${card.section})` : card.chapter;
    
    const progressPercent = Math.round((currentNum / totalNum) * 100);
    elements.studyProgressBar.style.width = `${progressPercent}%`;

    // Populate Card Front (Term)
    elements.cardChLabel.textContent = card.chapter;
    elements.cardTerm.innerHTML = card.term;
    renderMath(elements.cardTerm);

    // Populate Card Back (Definition)
    elements.cardSectionLabel.textContent = card.section ? `Section ${card.section}` : card.chapter;
    elements.cardDefinition.innerHTML = formatDefinitionHtml(card.definition);
    renderMath(elements.cardDefinition);

    // Update Next Button label if last card
    if (state.currentIndex === state.deck.length - 1) {
      elements.btnNextCard.innerHTML = `<span>Finish Deck</span> <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
    } else {
      elements.btnNextCard.innerHTML = `<span>Next</span> <span class="kbd-hint">→</span> <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>`;
    }

    // Prev Button state
    elements.btnPrevCard.disabled = state.currentIndex === 0;
  }

  function formatDefinitionHtml(rawText) {
    if (!rawText) return '';
    const blocks = rawText.split(/\n\s*\n/);
    if (blocks.length > 1) {
      return blocks.map(b => {
        b = b.trim();
        if (!b) return '';
        if (b.startsWith('<ul') || b.startsWith('<div class="def-table')) {
          return b;
        }
        return `<p class="def-paragraph">${b}</p>`;
      }).join('');
    }
    return rawText;
  }

  /**
   * Toggle 3D card flip
   */
  function flipCard() {
    if (isNavigating) return;
    state.isFlipped = !state.isFlipped;
    elements.flashcard.classList.toggle('flipped', state.isFlipped);
    elements.btnFlipCard.innerHTML = state.isFlipped ? 
      `<span>Show Term</span> <span class="kbd-hint">Space</span>` : 
      `<span>Flip Card</span> <span class="kbd-hint">Space</span>`;
  }

  let isNavigating = false;

  /**
   * Advance to next card or trigger completion
   * If definition is showing, flips back to term FIRST before transitioning
   */
  function nextCard() {
    if (isNavigating) return;

    if (state.currentIndex >= state.deck.length - 1) {
      showCompletionScreen();
      return;
    }

    if (state.isFlipped) {
      isNavigating = true;
      state.isFlipped = false;
      elements.flashcard.classList.remove('flipped');
      elements.btnFlipCard.innerHTML = `<span>Flip Card</span> <span class="kbd-hint">Space</span>`;
      
      // Wait for card flip animation to rotate back to term before changing card content
      setTimeout(() => {
        state.currentIndex++;
        renderCurrentCard();
        isNavigating = false;
      }, 300);
    } else {
      state.currentIndex++;
      renderCurrentCard();
    }
  }

  /**
   * Return to previous card
   * If definition is showing, flips back to term FIRST before transitioning
   */
  function prevCard() {
    if (isNavigating || state.currentIndex <= 0) return;

    if (state.isFlipped) {
      isNavigating = true;
      state.isFlipped = false;
      elements.flashcard.classList.remove('flipped');
      elements.btnFlipCard.innerHTML = `<span>Flip Card</span> <span class="kbd-hint">Space</span>`;

      setTimeout(() => {
        state.currentIndex--;
        renderCurrentCard();
        isNavigating = false;
      }, 300);
    } else {
      state.currentIndex--;
      renderCurrentCard();
    }
  }

  /**
   * Re-shuffle deck during session
   */
  function shuffleCurrentDeck() {
    state.deck = shuffleArray(state.deck);
    state.currentIndex = 0;
    renderCurrentCard();
  }

  /**
   * Show Completion Screen
   */
  function showCompletionScreen() {
    elements.completeCourseTitle.textContent = `${state.currentCourse.code}: ${state.currentCourse.title}`;
    elements.completeTotalCards.textContent = state.deck.length;
    elements.completeTotalChapters.textContent = state.selectedChapters.size;
    
    const chList = Array.from(state.selectedChapters).join(', ');
    elements.completeSummaryText.textContent = `You reviewed all ${state.deck.length} definitions across ${state.selectedChapters.size} chosen chapters (${chList}).`;

    setView('complete');
  }

  /**
   * Setup Event Listeners
   */
  function setupEventListeners() {
    // Brand Logo -> Return to Main Menu
    document.querySelector('.brand-wrapper').addEventListener('click', () => {
      setView('landing');
    });

    // Chapter selection navigation & controls
    elements.btnBackToCourses.addEventListener('click', () => setView('landing'));
    
    elements.btnSelectAllChapters.addEventListener('click', () => {
      if (!state.currentCourse) return;
      state.selectedChapters = new Set(state.currentCourse.chapters.map(c => c.name));
      renderChapterSelection();
    });

    elements.btnClearAllChapters.addEventListener('click', () => {
      state.selectedChapters.clear();
      renderChapterSelection();
    });

    elements.btnStartStudying.addEventListener('click', startStudySession);

    // Study View controls
    elements.btnExitStudy.addEventListener('click', () => {
      if (confirm('Leave current study session and return to chapter menu?')) {
        setView('chapters');
      }
    });

    elements.btnShuffleDeck.addEventListener('click', shuffleCurrentDeck);
    
    // Flipping mechanics (ONLY via dedicated Flip button or keyboard shortcuts per user preference)
    elements.btnFlipCard.addEventListener('click', (e) => {
      e.stopPropagation();
      flipCard();
    });

    elements.btnNextCard.addEventListener('click', nextCard);
    elements.btnPrevCard.addEventListener('click', prevCard);

    // Completion View navigation
    elements.btnRestartSession.addEventListener('click', () => {
      startStudySession();
    });

    elements.btnBackToChapterSelect.addEventListener('click', () => {
      setView('chapters');
    });

    elements.btnBackToMainMenu.addEventListener('click', () => {
      setView('landing');
    });

    // Desktop Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
      // Only active during study view
      if (state.currentView !== 'study') return;

      if (e.code === 'Space' || e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        flipCard();
      } else if (e.code === 'ArrowRight' || e.key === 'j' || e.key === 'J') {
        e.preventDefault();
        nextCard();
      } else if (e.code === 'ArrowLeft' || e.key === 'k' || e.key === 'K') {
        e.preventDefault();
        prevCard();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        shuffleCurrentDeck();
      } else if (e.code === 'Escape') {
        setView('chapters');
      }
    });
  }

  /**
   * Main App Initialization
   */
  function init() {
    if (window.FLASHCARD_DATA && window.FLASHCARD_DATA.courses) {
      state.courses = window.FLASHCARD_DATA.courses;
      renderCourseLanding();
      setupEventListeners();
      setView('landing');
      console.log(`Math Flashcards initialized with ${window.FLASHCARD_DATA.totalDefinitions} definitions across ${state.courses.length} courses.`);
    } else {
      console.error('FLASHCARD_DATA not found. Make sure definitions.js is loaded.');
    }
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();

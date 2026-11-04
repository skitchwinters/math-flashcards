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
    selectedCardIds: new Set(),
    expandedChapters: new Set(),
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
    btnToggleAllExpand: document.getElementById('btn-toggle-all-expand'),
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
   * Helper: Get all cards belonging to a chapter in current course
   */
  function getCardsInChapter(chapterName) {
    if (!state.currentCourse) return [];
    return state.currentCourse.cards.filter(c => c.chapter === chapterName);
  }

  /**
   * Helper: Calculate selection count in a chapter
   */
  function getChapterSelectionStats(chapterName) {
    const cards = getCardsInChapter(chapterName);
    const selectedCount = cards.filter(c => state.selectedCardIds.has(c.id)).length;
    return {
      total: cards.length,
      selected: selectedCount,
      all: cards.length > 0 && selectedCount === cards.length,
      none: selectedCount === 0,
      partial: selectedCount > 0 && selectedCount < cards.length
    };
  }

  /**
   * User selects a course -> navigate to Chapter Selection
   */
  function selectCourse(course) {
    state.currentCourse = course;
    elements.chapterCourseTitle.textContent = `${course.code}: ${course.title}`;
    elements.chapterCourseBadge.textContent = course.code;
    
    // Default: nothing selected and chapters collapsed per user directive
    state.selectedCardIds = new Set();
    state.expandedChapters = new Set();
    
    renderChapterSelection();
    setView('chapters');
  }

  /**
   * Render Chapter Selection View with expandable accordions and individual card checkboxes
   */
  function renderChapterSelection() {
    if (!state.currentCourse) return;
    elements.chapterGrid.innerHTML = '';

    state.currentCourse.chapters.forEach(ch => {
      const chapterCards = getCardsInChapter(ch.name);
      const isExpanded = state.expandedChapters.has(ch.name);
      const stats = getChapterSelectionStats(ch.name);

      const accordion = document.createElement('div');
      accordion.className = `chapter-accordion ${isExpanded ? 'expanded' : ''} ${stats.all ? 'full-selected' : stats.partial ? 'partial-selected' : 'none-selected'}`;
      accordion.dataset.chapter = ch.name;

      // Header row
      const header = document.createElement('div');
      header.className = 'chapter-header';
      header.innerHTML = `
        <div class="chapter-header-left">
          <div class="chapter-checkbox ${stats.all ? 'full' : stats.partial ? 'partial' : 'none'}" 
               role="checkbox" 
               aria-checked="${stats.all ? 'true' : stats.partial ? 'mixed' : 'false'}" 
               title="Toggle all in ${ch.name}">
            <svg class="icon-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <svg class="icon-partial" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </div>
          <div class="chapter-info">
            <h3>${ch.name}</h3>
            <p class="chapter-status-text">${stats.selected > 0 ? `<strong style="color: var(--accent-blue);">${stats.selected}</strong> of ${stats.total} selected` : `0 of ${stats.total} selected`}</p>
          </div>
        </div>
        <div class="chapter-header-right">
          <button class="btn-toggle-expand" aria-label="Expand or collapse ${ch.name}">
            <svg class="chevron-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>
        </div>
      `;

      // Clicking chapter checkbox toggles all cards in this chapter
      const checkboxEl = header.querySelector('.chapter-checkbox');
      checkboxEl.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleChapterAll(ch.name);
      });

      // Clicking header toggles accordion expand
      header.addEventListener('click', () => {
        toggleChapterAccordion(ch.name);
      });

      // Body (Cards List Drawer)
      const body = document.createElement('div');
      body.className = 'chapter-body';
      body.style.display = isExpanded ? 'block' : 'none';

      // Sub-actions bar
      const subBar = document.createElement('div');
      subBar.className = 'chapter-sub-bar';
      subBar.innerHTML = `
        <span class="chapter-sub-bar-count">${stats.selected > 0 ? `<strong style="color: var(--accent-blue);">${stats.selected}</strong> of ${stats.total} terms selected` : `0 of ${stats.total} terms selected`}</span>
        <div class="chapter-sub-actions">
          <button class="btn-sub-action btn-select-chapter-all">Select Chapter</button>
          <span class="sub-sep">•</span>
          <button class="btn-sub-action btn-deselect-chapter-all">Deselect Chapter</button>
        </div>
      `;

      subBar.querySelector('.btn-select-chapter-all').addEventListener('click', (e) => {
        e.stopPropagation();
        chapterCards.forEach(c => state.selectedCardIds.add(c.id));
        updateChapterUI(ch.name);
        updateSelectionSummary();
      });

      subBar.querySelector('.btn-deselect-chapter-all').addEventListener('click', (e) => {
        e.stopPropagation();
        chapterCards.forEach(c => state.selectedCardIds.delete(c.id));
        updateChapterUI(ch.name);
        updateSelectionSummary();
      });

      body.appendChild(subBar);

      // Cards Grid
      const cardsGrid = document.createElement('div');
      cardsGrid.className = 'chapter-cards-grid';

      chapterCards.forEach(card => {
        const isCardSelected = state.selectedCardIds.has(card.id);
        const cardItem = document.createElement('div');
        cardItem.className = `card-select-item ${isCardSelected ? 'selected' : ''}`;
        cardItem.dataset.cardId = card.id;
        cardItem.setAttribute('role', 'checkbox');
        cardItem.setAttribute('aria-checked', isCardSelected ? 'true' : 'false');

        cardItem.innerHTML = `
          <div class="card-item-checkbox">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <div class="card-item-content">
            <div class="card-item-term">${card.term}</div>
            ${card.section ? `<span class="card-item-section">Sec ${card.section}</span>` : ''}
          </div>
        `;

        cardItem.addEventListener('click', () => {
          toggleCardSelection(card.id, ch.name);
        });

        cardsGrid.appendChild(cardItem);
      });

      body.appendChild(cardsGrid);
      accordion.appendChild(header);
      accordion.appendChild(body);
      elements.chapterGrid.appendChild(accordion);
    });

    // Render KaTeX for mathematical notation in all term titles!
    renderMath(elements.chapterGrid);

    updateSelectionSummary();
    syncAccordionExpandStates();
  }

  /**
   * Toggle individual card selection
   */
  function toggleCardSelection(cardId, chapterName) {
    if (state.selectedCardIds.has(cardId)) {
      state.selectedCardIds.delete(cardId);
    } else {
      state.selectedCardIds.add(cardId);
    }
    updateChapterUI(chapterName);
    updateSelectionSummary();
  }

  /**
   * Toggle all cards in a specific chapter
   */
  function toggleChapterAll(chapterName) {
    const cards = getCardsInChapter(chapterName);
    const stats = getChapterSelectionStats(chapterName);
    
    if (stats.all) {
      cards.forEach(c => state.selectedCardIds.delete(c.id));
    } else {
      cards.forEach(c => state.selectedCardIds.add(c.id));
    }
    
    updateChapterUI(chapterName);
    updateSelectionSummary();
  }

  /**
   * Toggle accordion expansion for a specific chapter
   */
  function toggleChapterAccordion(chapterName) {
    if (state.expandedChapters.has(chapterName)) {
      state.expandedChapters.delete(chapterName);
    } else {
      state.expandedChapters.add(chapterName);
    }
    syncAccordionExpandStates();
  }

  /**
   * Toggle expand/collapse all chapters
   */
  function toggleAllExpand() {
    if (!state.currentCourse) return;
    const allChapterNames = state.currentCourse.chapters.map(ch => ch.name);
    if (state.expandedChapters.size === allChapterNames.length) {
      state.expandedChapters.clear();
    } else {
      state.expandedChapters = new Set(allChapterNames);
    }
    syncAccordionExpandStates();
  }

  /**
   * Update a single chapter's UI in-place without re-rendering the DOM
   */
  function updateChapterUI(chapterName) {
    const accordions = Array.from(elements.chapterGrid.querySelectorAll('.chapter-accordion'));
    const accordion = accordions.find(el => el.dataset.chapter === chapterName);
    if (!accordion) return;

    const stats = getChapterSelectionStats(chapterName);
    const checkbox = accordion.querySelector('.chapter-checkbox');
    const statusText = accordion.querySelector('.chapter-status-text');
    const subBarCount = accordion.querySelector('.chapter-sub-bar-count');

    // Update checkbox class & attributes
    checkbox.classList.remove('none', 'partial', 'full');
    accordion.classList.remove('none-selected', 'partial-selected', 'full-selected');

    if (stats.all) {
      checkbox.classList.add('full');
      accordion.classList.add('full-selected');
      checkbox.setAttribute('aria-checked', 'true');
    } else if (stats.partial) {
      checkbox.classList.add('partial');
      accordion.classList.add('partial-selected');
      checkbox.setAttribute('aria-checked', 'mixed');
    } else {
      checkbox.classList.add('none');
      accordion.classList.add('none-selected');
      checkbox.setAttribute('aria-checked', 'false');
    }

    if (statusText) {
      statusText.innerHTML = stats.selected > 0 
        ? `<strong style="color: var(--accent-blue);">${stats.selected}</strong> of ${stats.total} selected`
        : `0 of ${stats.total} selected`;
    }

    if (subBarCount) {
      subBarCount.innerHTML = stats.selected > 0 
        ? `<strong style="color: var(--accent-blue);">${stats.selected}</strong> of ${stats.total} terms selected`
        : `0 of ${stats.total} terms selected`;
    }

    // Update individual card items inside this chapter
    const cardItems = accordion.querySelectorAll('.card-select-item');
    cardItems.forEach(item => {
      const cardId = item.dataset.cardId;
      const isSelected = state.selectedCardIds.has(cardId);
      item.classList.toggle('selected', isSelected);
      item.setAttribute('aria-checked', isSelected ? 'true' : 'false');
    });
  }

  /**
   * Sync all selection UI across every chapter
   */
  function syncAllSelectionUI() {
    if (!state.currentCourse) return;
    state.currentCourse.chapters.forEach(ch => updateChapterUI(ch.name));
    updateSelectionSummary();
  }

  /**
   * Sync accordion open/close display and button label
   */
  function syncAccordionExpandStates() {
    if (!state.currentCourse) return;
    const allCount = state.currentCourse.chapters.length;
    const isAllExpanded = allCount > 0 && state.expandedChapters.size === allCount;

    if (elements.btnToggleAllExpand) {
      elements.btnToggleAllExpand.textContent = isAllExpanded ? 'Collapse All' : 'Expand All';
    }

    const accordions = elements.chapterGrid.querySelectorAll('.chapter-accordion');
    accordions.forEach(acc => {
      const chName = acc.dataset.chapter;
      const isExpanded = state.expandedChapters.has(chName);
      acc.classList.toggle('expanded', isExpanded);
      const body = acc.querySelector('.chapter-body');
      if (body) {
        body.style.display = isExpanded ? 'block' : 'none';
      }
    });
  }

  /**
   * Update selection count badge and enable/disable start button
   */
  function updateSelectionSummary() {
    if (!state.currentCourse) return;
    
    const totalSelected = state.selectedCardIds.size;
    elements.selectedCountBadge.innerHTML = `<strong>${totalSelected}</strong> definition${totalSelected === 1 ? '' : 's'} selected`;
    elements.btnStartStudying.disabled = totalSelected === 0;
    if (totalSelected === 0) {
      elements.btnStartStudying.innerHTML = `Select Cards to Start (0 Selected)`;
    } else {
      elements.btnStartStudying.innerHTML = `Start Studying (${totalSelected}) <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>`;
    }
  }

  /**
   * Start study session with selected cards
   */
  function startStudySession() {
    if (!state.currentCourse || state.selectedCardIds.size === 0) return;

    // Filter cards belonging to selected cards
    const eligibleCards = state.currentCourse.cards.filter(c => state.selectedCardIds.has(c.id));
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

    const uniqueChapters = Array.from(new Set(state.deck.map(c => c.chapter)));
    elements.completeTotalChapters.textContent = uniqueChapters.length;
    
    const chList = uniqueChapters.join(', ');
    elements.completeSummaryText.textContent = `You reviewed all ${state.deck.length} definitions across ${uniqueChapters.length} chosen chapter${uniqueChapters.length === 1 ? '' : 's'} (${chList}).`;

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
      state.selectedCardIds = new Set(state.currentCourse.cards.map(c => c.id));
      syncAllSelectionUI();
    });

    elements.btnClearAllChapters.addEventListener('click', () => {
      state.selectedCardIds.clear();
      syncAllSelectionUI();
    });

    if (elements.btnToggleAllExpand) {
      elements.btnToggleAllExpand.addEventListener('click', toggleAllExpand);
    }

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

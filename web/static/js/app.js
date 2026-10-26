/**
 * CampusConnect: Modern Responsive Web & Mobile PWA Application
 * Handles state management, real-time filtering, algorithmic match radar,
 * claims workflows, notifications, and PWA installation.
 */

class CampusConnectApp {
  constructor() {
    this.currentUser = null;
    this.demoUsers = [];
    this.activeTab = 'browse';
    this.items = [];
    this.claims = [];
    this.filters = {
      search: '',
      type: 'ALL',
      category: 'ALL',
      status: 'ALL'
    };
    this.selectedPhotoBase64 = null;
    this.searchDebounceTimer = null;
    this.deferredPrompt = null;
    this.mySubtab = 'reports';

    this.init();
  }

  async init() {
    this.initTheme();
    this.initPWA();
    await this.loadCurrentUser();
    await this.loadDemoUsers();
    await this.loadItems();
    this.updateNotificationBadge();
    
    // Set default date for report form to today
    const dateInput = document.getElementById('reportDate');
    if (dateInput) {
      dateInput.value = new Date().toISOString().split('T')[0];
    }
  }

  // -------------------------------------------------------------
  // Theme & PWA Management
  // -------------------------------------------------------------

  initTheme() {
    const savedTheme = localStorage.getItem('cc_theme_ruby') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    this.updateThemeIcons(savedTheme);
  }

  toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const next = current === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('cc_theme_ruby', next);
    this.updateThemeIcons(next);
  }

  updateThemeIcons(theme) {
    const iconDark = document.getElementById('themeIconDark');
    const iconLight = document.getElementById('themeIconLight');
    if (iconDark && iconLight) {
      if (theme === 'dark') {
        iconDark.style.display = 'block';
        iconLight.style.display = 'none';
      } else {
        iconDark.style.display = 'none';
        iconLight.style.display = 'block';
      }
    }
  }

  initPWA() {
    // Register Service Worker
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch((err) => {
          console.warn('[PWA] ServiceWorker registration error:', err);
        });
      });
    }

    // Capture install prompt for mobile & desktop install button
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e;
      const installBtn = document.getElementById('pwaInstallBtn');
      if (installBtn) {
        installBtn.style.display = 'inline-flex';
      }
    });

    window.addEventListener('appinstalled', () => {
      this.deferredPrompt = null;
      const installBtn = document.getElementById('pwaInstallBtn');
      if (installBtn) installBtn.style.display = 'none';
      this.showToast('CampusConnect installed successfully!', 'success');
    });
  }

  async promptPwaInstall() {
    if (!this.deferredPrompt) return;
    this.deferredPrompt.prompt();
    const { outcome } = await this.deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      const installBtn = document.getElementById('pwaInstallBtn');
      if (installBtn) installBtn.style.display = 'none';
    }
    this.deferredPrompt = null;
  }

  // -------------------------------------------------------------
  // User Authentication & Demo Switcher
  // -------------------------------------------------------------

  async loadCurrentUser() {
    try {
      const res = await fetch('/api/auth/me');
      const data = await res.json();
      if (data.authenticated && data.user) {
        this.currentUser = data.user;
        this.renderUserUI();
      }
    } catch (err) {
      console.error('Failed to load current user:', err);
    }
  }

  renderUserUI() {
    if (!this.currentUser) return;
    
    const nameEl = document.getElementById('userName');
    const roleBadgeEl = document.getElementById('userRoleBadge');
    const avatarEl = document.getElementById('userAvatar');
    const adminNoticeEl = document.getElementById('adminBadgeNotice');
    const claimsDescEl = document.getElementById('claimsPaneDesc');

    if (nameEl) nameEl.textContent = this.currentUser.full_name;
    if (roleBadgeEl) roleBadgeEl.textContent = this.currentUser.role.toUpperCase();
    if (avatarEl) avatarEl.textContent = this.currentUser.full_name.charAt(0).toUpperCase();

    const isAdmin = this.currentUser.role === 'admin';
    if (adminNoticeEl) adminNoticeEl.style.display = isAdmin ? 'inline-flex' : 'none';
    if (claimsDescEl) {
      claimsDescEl.textContent = isAdmin
        ? 'Admin Verification Queue: Inspect submitted proof descriptions and authorize property handovers.'
        : 'Track the verification status of your submitted ownership claims and pickup instructions.';
    }
  }

  async loadDemoUsers() {
    try {
      const res = await fetch('/api/auth/demo-users');
      const data = await res.json();
      if (data.success) {
        this.demoUsers = data.users;
      }
    } catch (err) {
      console.error('Failed to load demo users:', err);
    }
  }

  openUserSwitcherModal() {
    const listEl = document.getElementById('demoUsersList');
    if (!listEl) return;

    listEl.innerHTML = this.demoUsers.map((u) => {
      const isActive = this.currentUser && this.currentUser.id === u.id;
      const roleColor = u.role === 'admin' ? 'badge-admin' : 'badge-found';
      return `
        <div class="demo-user-card ${isActive ? 'active' : ''}" onclick="app.switchUser(${u.id})">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div class="user-avatar" style="width: 36px; height: 36px; font-size: 0.95rem;">
              ${u.full_name.charAt(0)}
            </div>
            <div>
              <div style="font-weight: 700; font-size: 0.95rem;">${u.full_name}</div>
              <div class="text-muted text-sm">${u.email}</div>
            </div>
          </div>
          <div>
            <span class="badge ${roleColor}">${u.role.toUpperCase()}</span>
          </div>
        </div>
      `;
    }).join('');

    this.openModal('userSwitcherModal');
  }

  async switchUser(userId) {
    try {
      const res = await fetch('/api/auth/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      const data = await res.json();
      if (data.success) {
        this.currentUser = data.user;
        this.renderUserUI();
        this.closeModal('userSwitcherModal');
        this.showToast(`Switched account to ${this.currentUser.full_name}`, 'info');
        
        // Refresh view
        await this.loadItems();
        this.updateNotificationBadge();
        if (this.activeTab === 'claims') this.loadClaims();
        if (this.activeTab === 'my-items') this.loadMyItems();
      }
    } catch (err) {
      this.showToast('Failed to switch user', 'error');
    }
  }

  // -------------------------------------------------------------
  // Navigation & Tabs
  // -------------------------------------------------------------

  navigate(tabName) {
    this.activeTab = tabName;

    // Update Desktop Nav
    document.querySelectorAll('.desktop-nav .nav-item').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update Mobile Bottom Nav
    document.querySelectorAll('.mobile-bottom-nav .bottom-nav-item').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update Tab Panes
    document.querySelectorAll('.tab-pane').forEach((pane) => {
      pane.classList.remove('active');
    });

    const targetPane = document.getElementById(`tab-${tabName}`);
    if (targetPane) {
      targetPane.classList.add('active');
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Tab-specific initializers
    if (tabName === 'matches') {
      this.populateMatchItemSelector();
    } else if (tabName === 'claims') {
      this.loadClaims();
    } else if (tabName === 'my-items') {
      this.loadMyItems();
    } else if (tabName === 'analytics') {
      this.loadAnalytics();
    }
  }

  // -------------------------------------------------------------
  // Items Catalog & Filtering
  // -------------------------------------------------------------

  async loadItems() {
    const params = new URLSearchParams();
    if (this.filters.type !== 'ALL') params.set('type', this.filters.type);
    if (this.filters.category !== 'ALL') params.set('category', this.filters.category);
    if (this.filters.status !== 'ALL') params.set('status', this.filters.status);
    if (this.filters.search.trim()) params.set('search', this.filters.search.trim());

    try {
      const res = await fetch(`/api/items?${params.toString()}`);
      const data = await res.json();
      if (data.success) {
        this.items = data.items;
        this.renderItemsGrid();
      }
    } catch (err) {
      console.error('Failed to load items:', err);
    }
  }

  renderItemsGrid() {
    const gridEl = document.getElementById('itemsGrid');
    const countEl = document.getElementById('catalogCount');
    const emptyEl = document.getElementById('itemsEmptyState');

    if (!gridEl) return;

    if (countEl) {
      countEl.textContent = `Showing ${this.items.length} campus reports`;
    }

    if (this.items.length === 0) {
      gridEl.innerHTML = '';
      if (emptyEl) emptyEl.style.display = 'block';
      return;
    }

    if (emptyEl) emptyEl.style.display = 'none';

    gridEl.innerHTML = this.items.map((it) => {
      const isLost = it.type === 'LOST';
      const badgeClass = isLost ? 'badge-lost' : 'badge-found';
      const statusClass = it.status === 'OPEN' ? 'status-open' : (it.status === 'CLAIM_PENDING' ? 'status-pending' : 'status-returned');
      const catIcon = this.getCategoryIcon(it.category);

      const photoHtml = it.image_path
        ? `<img src="/${it.image_path}" class="card-img" alt="${it.title}">`
        : `<div class="card-placeholder-icon">${catIcon}</div>`;

      const matchChip = (it.status === 'OPEN' && it.match_count > 0)
        ? `<div class="match-radar-chip" onclick="event.stopPropagation(); app.openMatchRadarForItem(${it.id})">
             <span>🤖</span> ${it.match_count} Smart Match${it.match_count > 1 ? 'es' : ''} Found
           </div>`
        : '';

      const claimActionBtn = (!isLost && it.status === 'OPEN')
        ? `<button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); app.openClaimModal(${it.id})">
             ✋ Claim Item
           </button>`
        : '';

      return `
        <div class="item-card" onclick="app.openItemDetails(${it.id})">
          <div class="card-media">
            ${photoHtml}
            <span class="badge-type ${badgeClass}">${it.type}</span>
            <span class="badge-status ${statusClass}">${it.status}</span>
          </div>
          <div class="card-body">
            <span class="card-category-pill">${catIcon} ${it.category}</span>
            <h3 class="card-title">${it.title}</h3>
            
            <div class="card-meta-row">
              <span class="card-meta-icon">📍</span>
              <span>${it.location}</span>
            </div>
            <div class="card-meta-row">
              <span class="card-meta-icon">📅</span>
              <span>${it.event_date}</span>
            </div>

            <p class="card-desc-snippet">${it.description}</p>
            
            ${matchChip}

            <div class="card-footer">
              <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); app.openItemDetails(${it.id})">
                Inspect
              </button>
              ${claimActionBtn}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  getCategoryIcon(category) {
    const map = {
      'Electronics': '💻',
      'Identity cards': '🪪',
      'Accessories': '⌚',
      'Books and stationery': '📚',
      'Personal belongings': '🎒',
      'Clothing': '👕',
      'Keys': '🔑',
      'Other': '📦'
    };
    return map[category] || '📦';
  }

  onSearchInput(val) {
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) clearBtn.style.display = val ? 'block' : 'none';

    clearTimeout(this.searchDebounceTimer);
    this.searchDebounceTimer = setTimeout(() => {
      this.filters.search = val;
      this.loadItems();
    }, 280);
  }

  clearSearch() {
    const input = document.getElementById('searchInput');
    if (input) input.value = '';
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) clearBtn.style.display = 'none';
    this.filters.search = '';
    this.loadItems();
  }

  setTypeFilter(typeVal) {
    this.filters.type = typeVal;
    document.querySelectorAll('.type-filter-segmented .seg-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.type === typeVal);
    });
    this.loadItems();
  }

  setCategoryFilter(catVal) {
    this.filters.category = catVal;
    document.querySelectorAll('.category-scroll .chip').forEach((chip) => {
      chip.classList.toggle('active', chip.dataset.cat === catVal);
    });
    this.loadItems();
  }

  setStatusFilter(statusVal) {
    this.filters.status = statusVal;
    this.loadItems();
  }

  resetAllFilters() {
    this.filters = { search: '', type: 'ALL', category: 'ALL', status: 'ALL' };
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = '';
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) clearBtn.style.display = 'none';

    document.querySelectorAll('.type-filter-segmented .seg-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.type === 'ALL');
    });
    document.querySelectorAll('.category-scroll .chip').forEach((chip) => {
      chip.classList.toggle('active', chip.dataset.cat === 'ALL');
    });
    const statusSelect = document.getElementById('statusFilter');
    if (statusSelect) statusSelect.value = 'ALL';

    this.loadItems();
  }

  // -------------------------------------------------------------
  // Item Details Modal
  // -------------------------------------------------------------

  async openItemDetails(itemId) {
    try {
      const res = await fetch(`/api/items/${itemId}`);
      const data = await res.json();
      if (!data.success || !data.item) return;

      const it = data.item;
      const isLost = it.type === 'LOST';
      const badgeClass = isLost ? 'badge-lost' : 'badge-found';
      const catIcon = this.getCategoryIcon(it.category);

      const contentEl = document.getElementById('itemDetailsContent');
      if (!contentEl) return;

      const imgHtml = it.image_path
        ? `<div style="text-align: center; margin-bottom: 16px;">
             <img src="/${it.image_path}" style="max-height: 280px; width: 100%; object-fit: contain; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
           </div>`
        : '';

      const claimBtnHtml = (!isLost && it.status === 'OPEN')
        ? `<button class="btn btn-primary" onclick="app.closeModal('itemDetailsModal'); app.openClaimModal(${it.id})">
             ✋ Claim Item Ownership
           </button>`
        : '';

      const matchBtnHtml = (it.status === 'OPEN')
        ? `<button class="btn btn-secondary" onclick="app.closeModal('itemDetailsModal'); app.openMatchRadarForItem(${it.id})">
             🤖 Smart Match Radar
           </button>`
        : '';

      const canDelete = this.currentUser && (it.user_id === this.currentUser.id || this.currentUser.role === 'admin');
      const deleteBtnHtml = canDelete
        ? `<button class="btn btn-danger" onclick="app.deleteItem(${it.id})">
             🗑️ Delete
           </button>`
        : '';

      contentEl.innerHTML = `
        ${imgHtml}
        <div style="display: flex; gap: 8px; margin-bottom: 10px;">
          <span class="badge ${badgeClass}">${it.type}</span>
          <span class="badge status-open">${it.status}</span>
          <span class="badge badge-found" style="background: var(--bg-glass);">${catIcon} ${it.category}</span>
        </div>

        <h2 style="font-size: 1.4rem; margin-bottom: 8px;">${it.title}</h2>
        
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 14px; margin-bottom: 14px;">
          <div class="card-meta-row" style="margin-bottom: 6px;">
            <strong style="width: 110px;">📍 Location:</strong> <span>${it.location}</span>
          </div>
          <div class="card-meta-row" style="margin-bottom: 6px;">
            <strong style="width: 110px;">📅 Date:</strong> <span>${it.event_date}</span>
          </div>
          <div class="card-meta-row" style="margin-bottom: 6px;">
            <strong style="width: 110px;">👤 Reported By:</strong> <span>${it.owner_name} (${it.owner_role.toUpperCase()})</span>
          </div>
          <div class="card-meta-row">
            <strong style="width: 110px;">🕒 Logged At:</strong> <span>${it.created_at ? it.created_at.slice(0, 16) : 'Recently'}</span>
          </div>
        </div>

        <div style="margin-bottom: 20px;">
          <h4 style="font-size: 0.95rem; margin-bottom: 6px; color: var(--text-secondary);">Item Description</h4>
          <p style="font-size: 0.92rem; line-height: 1.5; color: var(--text-main); background: var(--bg-card); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            ${it.description}
          </p>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border-color); padding-top: 14px;">
          ${deleteBtnHtml}
          ${matchBtnHtml}
          ${claimBtnHtml}
        </div>
      `;

      this.openModal('itemDetailsModal');
    } catch (err) {
      console.error('Failed to open details modal:', err);
    }
  }

  async deleteItem(itemId) {
    if (!confirm('Are you sure you want to permanently delete this report?')) return;
    try {
      const res = await fetch(`/api/items/${itemId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        this.closeModal('itemDetailsModal');
        this.showToast('Report deleted successfully', 'success');
        await this.loadItems();
      } else {
        this.showToast(data.error || 'Failed to delete report', 'error');
      }
    } catch (err) {
      this.showToast('Network error while deleting item', 'error');
    }
  }

  // -------------------------------------------------------------
  // Smart Match Radar
  // -------------------------------------------------------------

  populateMatchItemSelector() {
    const selectEl = document.getElementById('matchItemSelect');
    if (!selectEl) return;

    selectEl.innerHTML = '<option value="">Select an item to scan...</option>' +
      this.items.filter(it => it.status === 'OPEN').map(it => `
        <option value="${it.id}">[${it.type}] #${it.id} ${it.title} (${it.category})</option>
      `).join('');
  }

  onMatchItemSelected(itemId) {
    if (itemId) {
      this.fetchAndRenderMatches(itemId);
    }
  }

  runMatchScanForCurrentItem() {
    const selectEl = document.getElementById('matchItemSelect');
    if (selectEl && selectEl.value) {
      this.fetchAndRenderMatches(selectEl.value);
    } else {
      this.showToast('Please pick an item from the dropdown first', 'info');
    }
  }

  openMatchRadarForItem(itemId) {
    this.navigate('matches');
    const selectEl = document.getElementById('matchItemSelect');
    if (selectEl) {
      selectEl.value = itemId;
      this.fetchAndRenderMatches(itemId);
    }
  }

  async fetchAndRenderMatches(itemId) {
    const area = document.getElementById('matchesResultsArea');
    if (!area) return;

    area.innerHTML = `
      <div style="text-align: center; padding: 40px;">
        <div style="font-size: 2rem; animation: spin 1s linear infinite;">⏳</div>
        <p style="margin-top: 10px; color: var(--text-secondary);">Calculating algorithmic term Jaccard similarity, category matching, and campus location distance...</p>
      </div>
    `;

    try {
      const res = await fetch(`/api/items/${itemId}/matches`);
      const data = await res.json();

      if (!data.success) {
        area.innerHTML = `<div class="empty-state"><h3>Unable to compute matches</h3><p>${data.error}</p></div>`;
        return;
      }

      const matches = data.matches;
      const source = data.source_item;

      if (matches.length === 0) {
        area.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <h3>No Counterpart Matches Found</h3>
            <p>No currently active reports meet the algorithmic confidence threshold for <strong>${source.title}</strong>.</p>
          </div>
        `;
        return;
      }

      area.innerHTML = `
        <div style="margin-bottom: 16px;">
          <span class="text-muted text-sm">Found <strong>${matches.length}</strong> counterpart candidates for:</span>
          <h3 style="color: #818cf8; font-size: 1.15rem; margin-top: 2px;">${source.type} #${source.id}: ${source.title}</h3>
        </div>
        <div class="match-results-grid">
          ${matches.map(m => {
            const target = m.target_item;
            const isFoundTarget = target.type === 'FOUND';
            const claimBtn = isFoundTarget
              ? `<button class="btn btn-sm btn-primary" onclick="app.openClaimModal(${target.id})">✋ Claim</button>`
              : '';

            return `
              <div class="match-result-card card">
                <div class="match-score-gauge">
                  <span class="match-pct">${m.overall_score}%</span>
                  <span class="match-pct-label">Confidence</span>
                </div>

                <div class="match-content">
                  <div style="display: flex; gap: 6px; align-items: center; margin-bottom: 4px;">
                    <span class="badge ${target.type === 'LOST' ? 'badge-lost' : 'badge-found'}">${target.type}</span>
                    <span class="text-muted text-sm">#${target.id} • ${target.category}</span>
                  </div>
                  <h3>${target.title}</h3>
                  <div class="text-sm text-muted">📍 ${target.location} • 📅 ${target.event_date}</div>

                  <div class="match-breakdown-bars">
                    <div class="breakdown-bar-item">
                      <div class="breakdown-label"><span>Category</span><span>${m.category_score}%</span></div>
                      <div class="bar-track"><div class="bar-fill" style="width: ${m.category_score}%;"></div></div>
                    </div>
                    <div class="breakdown-bar-item">
                      <div class="breakdown-label"><span>Keywords</span><span>${m.keyword_score}%</span></div>
                      <div class="bar-track"><div class="bar-fill" style="width: ${m.keyword_score}%;"></div></div>
                    </div>
                    <div class="breakdown-bar-item">
                      <div class="breakdown-label"><span>Location</span><span>${m.location_score}%</span></div>
                      <div class="bar-track"><div class="bar-fill" style="width: ${m.location_score}%;"></div></div>
                    </div>
                    <div class="breakdown-bar-item">
                      <div class="breakdown-label"><span>Date Proximity</span><span>${m.date_score}%</span></div>
                      <div class="bar-track"><div class="bar-fill" style="width: ${m.date_score}%;"></div></div>
                    </div>
                  </div>

                  <div class="match-rationale-box">
                    <strong>Algorithmic Rationale:</strong> ${m.explanation}
                  </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px;">
                  <button class="btn btn-sm btn-secondary" onclick="app.openItemDetails(${target.id})">Inspect</button>
                  ${claimBtn}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    } catch (err) {
      area.innerHTML = `<div class="empty-state"><h3>Network error</h3><p>Could not load matches.</p></div>`;
    }
  }

  // -------------------------------------------------------------
  // Report Item Submission
  // -------------------------------------------------------------

  onReportTypeChange(type) {
    const title = document.querySelector('.report-title');
    if (title) {
      title.textContent = type === 'LOST' ? '📝 Report Lost Item' : '📦 Report Found Item';
    }
  }

  setReportLocation(loc) {
    const input = document.getElementById('reportLocation');
    if (input) input.value = loc;
  }

  handlePhotoSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      this.showToast('Photo size exceeds 10MB limit', 'error');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      this.selectedPhotoBase64 = e.target.result;
      const preview = document.getElementById('dropzonePreview');
      const content = document.getElementById('dropzoneContent');
      const previewImg = document.getElementById('previewImg');

      if (preview && content && previewImg) {
        previewImg.src = this.selectedPhotoBase64;
        preview.style.display = 'block';
        content.style.display = 'none';
      }
    };
    reader.readAsDataURL(file);
  }

  removePhoto() {
    this.selectedPhotoBase64 = null;
    const fileInput = document.getElementById('reportPhoto');
    if (fileInput) fileInput.value = '';

    const preview = document.getElementById('dropzonePreview');
    const content = document.getElementById('dropzoneContent');
    if (preview && content) {
      preview.style.display = 'none';
      content.style.display = 'block';
    }
  }

  async handleReportSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('submitReportBtn');
    if (btn) btn.disabled = true;

    const reportType = document.querySelector('input[name="report_type"]:checked').value;
    const title = document.getElementById('reportTitle').value.trim();
    const category = document.getElementById('reportCategory').value;
    const eventDate = document.getElementById('reportDate').value;
    const location = document.getElementById('reportLocation').value.trim();
    const description = document.getElementById('reportDesc').value.trim();

    const payload = {
      type: reportType,
      title: title,
      category: category,
      event_date: eventDate,
      location: location,
      description: description,
      image_base64: this.selectedPhotoBase64
    };

    try {
      const res = await fetch('/api/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (data.success) {
        this.showToast(data.message, 'success');
        
        if (data.matches_triggered > 0) {
          this.showToast(`🤖 Smart Match Radar alert sent to ${data.matches_triggered} candidate owners!`, 'info');
        }

        // Reset form
        document.getElementById('reportForm').reset();
        this.removePhoto();

        // Refresh items and go to catalog
        await this.loadItems();
        this.navigate('browse');
      } else {
        this.showToast(data.error || 'Failed to submit report', 'error');
      }
    } catch (err) {
      this.showToast('Network error submitting report', 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // -------------------------------------------------------------
  // Claims Management Hub
  // -------------------------------------------------------------

  async loadClaims(statusFilter = 'ALL') {
    const container = document.getElementById('claimsListContainer');
    if (!container) return;

    container.innerHTML = `<div style="text-align: center; padding: 40px;">⏳ Loading claims queue...</div>`;

    try {
      const params = statusFilter !== 'ALL' ? `?status=${statusFilter}` : '';
      const res = await fetch(`/api/claims${params}`);
      const data = await res.json();

      if (!data.success) {
        container.innerHTML = `<div class="empty-state"><h3>Error loading claims</h3><p>${data.error}</p></div>`;
        return;
      }

      this.claims = data.claims;

      if (this.claims.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">🛡️</div>
            <h3>No Claims in Queue</h3>
            <p>There are no ownership claims matching this filter.</p>
          </div>
        `;
        return;
      }

      const isAdmin = this.currentUser && this.currentUser.role === 'admin';

      container.innerHTML = this.claims.map(c => {
        let statusBadge = '<span class="badge status-pending">⏳ PENDING</span>';
        if (c.status === 'APPROVED') statusBadge = '<span class="badge status-returned">✅ APPROVED</span>';
        if (c.status === 'REJECTED') statusBadge = '<span class="badge badge-lost">❌ REJECTED</span>';

        const adminActions = (isAdmin && c.status === 'PENDING')
          ? `<button class="btn btn-sm btn-primary" onclick="app.openReviewClaimModal(${c.id})">
               🛡️ Review Claim
             </button>`
          : '';

        const notesBox = c.verification_notes
          ? `<div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 8px;">
               <strong>Verification Note:</strong> ${c.verification_notes}
             </div>`
          : '';

        return `
          <div class="claim-card card">
            <div>
              <div class="claim-title-row">
                ${statusBadge}
                <strong style="font-size: 1.05rem;">Claim #${c.id} on: ${c.item_title}</strong>
              </div>
              <div class="text-sm text-muted">
                Claimant: <strong>${c.claimant_name}</strong> (${c.claimant_email}) • Submitted: ${c.created_at ? c.created_at.slice(0, 16) : ''}
              </div>

              <div class="claim-proof-box">
                <strong>Distinguishing Proof Given:</strong>
                <p style="margin-top: 4px;">${c.proof_description}</p>
              </div>

              ${notesBox}
            </div>

            <div class="claim-actions">
              <button class="btn btn-sm btn-secondary" onclick="app.openItemDetails(${c.item_id})">View Item</button>
              ${adminActions}
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      container.innerHTML = `<div class="empty-state"><h3>Failed to fetch claims</h3></div>`;
    }
  }

  filterClaims(status) {
    document.querySelectorAll('.claims-filter-row .chip').forEach(c => {
      c.classList.toggle('active', c.dataset.claimStatus === status);
    });
    this.loadClaims(status);
  }

  openClaimModal(itemId) {
    const item = this.items.find(i => i.id === itemId);
    if (!item) return;

    const idInput = document.getElementById('claimItemId');
    const titleEl = document.getElementById('claimItemTitle');
    const locEl = document.getElementById('claimItemLocation');

    if (idInput) idInput.value = item.id;
    if (titleEl) titleEl.textContent = `${item.title} (${item.category})`;
    if (locEl) locEl.textContent = `Found at: ${item.location} on ${item.event_date}`;

    this.openModal('claimModal');
  }

  async handleClaimSubmit(e) {
    e.preventDefault();
    const itemId = document.getElementById('claimItemId').value;
    const proof = document.getElementById('claimProofText').value.trim();

    try {
      const res = await fetch('/api/claims', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, proof_description: proof })
      });
      const data = await res.json();

      if (data.success) {
        this.closeModal('claimModal');
        this.showToast(data.message, 'success');
        document.getElementById('claimSubmitForm').reset();
        await this.loadItems();
        if (this.activeTab === 'claims') this.loadClaims();
      } else {
        this.showToast(data.error || 'Failed to submit claim', 'error');
      }
    } catch (err) {
      this.showToast('Network error submitting claim', 'error');
    }
  }

  openReviewClaimModal(claimId) {
    const claim = this.claims.find(c => c.id === claimId);
    if (!claim) return;

    const bodyEl = document.getElementById('reviewClaimBody');
    if (!bodyEl) return;

    bodyEl.innerHTML = `
      <div class="card mb-3">
        <h4>${claim.item_title}</h4>
        <div class="text-sm text-muted">Claimed by: ${claim.claimant_name} (${claim.claimant_email})</div>
        <div class="claim-proof-box mt-2">
          <strong>Proof Description:</strong>
          <p>${claim.proof_description}</p>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label" for="reviewNotesInput">Admin Verification Notes</label>
        <textarea id="reviewNotesInput" class="form-input" rows="3" placeholder="Notes on verified student ID, serial number match, or reason for decision..."></textarea>
      </div>

      <div class="form-actions mt-3">
        <button class="btn btn-danger" onclick="app.submitClaimDecision(${claim.id}, 'reject')">
          ❌ Reject Claim
        </button>
        <button class="btn btn-success" onclick="app.submitClaimDecision(${claim.id}, 'approve')">
          ✅ Authorize & Approve Handover
        </button>
      </div>
    `;

    this.openModal('reviewClaimModal');
  }

  async submitClaimDecision(claimId, action) {
    const notesInput = document.getElementById('reviewNotesInput');
    const notes = notesInput ? notesInput.value.trim() : '';

    try {
      const res = await fetch(`/api/claims/${claimId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action, notes: notes })
      });
      const data = await res.json();

      if (data.success) {
        this.closeModal('reviewClaimModal');
        this.showToast(data.message, 'success');
        await this.loadClaims();
        await this.loadItems();
      } else {
        this.showToast(data.error || 'Failed to review claim', 'error');
      }
    } catch (err) {
      this.showToast('Network error reviewing claim', 'error');
    }
  }

  // -------------------------------------------------------------
  // My Reports & Activity Tab
  // -------------------------------------------------------------

  async loadMyItems() {
    if (!this.currentUser) return;
    
    try {
      const res = await fetch(`/api/items?mine=true`);
      const data = await res.json();
      const myItems = data.success ? data.items : [];

      const countEl = document.getElementById('myReportsCount');
      if (countEl) countEl.textContent = myItems.length;

      const reportsArea = document.getElementById('myReportsArea');
      if (reportsArea) {
        if (myItems.length === 0) {
          reportsArea.innerHTML = `<div class="empty-state"><h3>You have not submitted any reports yet</h3><p>Use the Report tab to submit your first item.</p></div>`;
        } else {
          reportsArea.innerHTML = myItems.map(it => `
            <div class="item-card card">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <span class="badge ${it.type === 'LOST' ? 'badge-lost' : 'badge-found'}">${it.type}</span>
                <span class="badge status-open">${it.status}</span>
              </div>
              <h3 class="card-title">${it.title}</h3>
              <div class="text-sm text-muted">📍 ${it.location} • 📅 ${it.event_date}</div>
              <p class="card-desc-snippet">${it.description}</p>
              <div class="card-footer">
                <button class="btn btn-sm btn-secondary" onclick="app.openItemDetails(${it.id})">Details</button>
                <button class="btn btn-sm btn-danger" onclick="app.deleteItem(${it.id})">Delete</button>
              </div>
            </div>
          `).join('');
        }
      }

      // Also fetch user's claims
      const claimsRes = await fetch('/api/claims');
      const claimsData = await claimsRes.json();
      const myClaims = claimsData.success ? claimsData.claims : [];

      const claimsCountEl = document.getElementById('myClaimsCount');
      if (claimsCountEl) claimsCountEl.textContent = myClaims.length;

      const claimsArea = document.getElementById('myClaimsArea');
      if (claimsArea) {
        if (myClaims.length === 0) {
          claimsArea.innerHTML = `<div class="empty-state"><h3>No claims filed by you</h3><p>If you see your lost item in the catalog, tap "Claim Item" to submit proof.</p></div>`;
        } else {
          claimsArea.innerHTML = myClaims.map(c => `
            <div class="claim-card card">
              <div>
                <strong style="font-size: 1.05rem;">Claim #${c.id}: ${c.item_title}</strong>
                <div class="text-sm text-muted">Status: <strong>${c.status}</strong></div>
                <div class="claim-proof-box mt-2">
                  <strong>Proof Provided:</strong> ${c.proof_description}
                </div>
                ${c.verification_notes ? `<div class="text-sm text-muted mt-2"><strong>Notes:</strong> ${c.verification_notes}</div>` : ''}
              </div>
              <button class="btn btn-sm btn-secondary" onclick="app.openItemDetails(${c.item_id})">View Item</button>
            </div>
          `).join('');
        }
      }

    } catch (err) {
      console.error('Failed to load my activity:', err);
    }
  }

  switchMySubtab(subtab) {
    this.mySubtab = subtab;
    const reportsArea = document.getElementById('myReportsArea');
    const claimsArea = document.getElementById('myClaimsArea');
    const buttons = document.querySelectorAll('.my-items-tabs .subtab-btn');

    if (buttons.length >= 2) {
      buttons[0].classList.toggle('active', subtab === 'reports');
      buttons[1].classList.toggle('active', subtab === 'claims');
    }

    if (reportsArea && claimsArea) {
      reportsArea.style.display = subtab === 'reports' ? 'grid' : 'none';
      claimsArea.style.display = subtab === 'claims' ? 'flex' : 'none';
    }
  }

  // -------------------------------------------------------------
  // Analytics & Insights
  // -------------------------------------------------------------

  async loadAnalytics() {
    try {
      const res = await fetch('/api/analytics');
      const data = await res.json();
      if (!data.success) return;

      const kpis = data.kpis;
      document.getElementById('kpiTotalItems').textContent = kpis.total_items;
      document.getElementById('kpiRecoveryRate').textContent = `${kpis.recovery_rate}%`;
      document.getElementById('kpiPendingClaims').textContent = kpis.pending_claims;
      document.getElementById('kpiReturnedItems').textContent = kpis.returned_items;

      // Category Chart Bars
      const catContainer = document.getElementById('categoryChartContainer');
      if (catContainer && data.categories) {
        const total = Object.values(data.categories).reduce((a, b) => a + b, 0) || 1;
        catContainer.innerHTML = Object.entries(data.categories).map(([cat, count]) => {
          const pct = Math.round((count / total) * 100);
          return `
            <div class="chart-bar-row">
              <div class="chart-bar-info">
                <span>${cat}</span>
                <span><strong>${count}</strong> (${pct}%)</span>
              </div>
              <div class="chart-bar-track">
                <div class="chart-bar-fill" style="width: ${pct}%;"></div>
              </div>
            </div>
          `;
        }).join('');
      }

      // Hotspots
      const spotsContainer = document.getElementById('hotspotsContainer');
      if (spotsContainer && data.locations) {
        spotsContainer.innerHTML = Object.entries(data.locations).map(([loc, count]) => `
          <div class="hotspot-item">
            <span>📍 ${loc}</span>
            <span class="badge badge-found">${count} reports</span>
          </div>
        `).join('');
      }

    } catch (err) {
      console.error('Failed to load analytics:', err);
    }
  }

  downloadCsvExport() {
    window.location.href = '/api/export/csv';
  }

  // -------------------------------------------------------------
  // Notifications Center
  // -------------------------------------------------------------

  async updateNotificationBadge() {
    if (!this.currentUser) return;
    try {
      const res = await fetch('/api/notifications?unread=true');
      const data = await res.json();
      if (data.success) {
        const badge = document.getElementById('notifBadge');
        if (badge) {
          if (data.unread_count > 0) {
            badge.textContent = data.unread_count;
            badge.style.display = 'flex';
          } else {
            badge.style.display = 'none';
          }
        }
      }
    } catch (err) {
      console.warn('Could not update notif badge:', err);
    }
  }

  async openNotificationsModal() {
    const listEl = document.getElementById('notificationsList');
    if (!listEl) return;

    listEl.innerHTML = `<div style="text-align: center; padding: 20px;">⏳ Loading notifications...</div>`;
    this.openModal('notificationsModal');

    try {
      const res = await fetch('/api/notifications');
      const data = await res.json();

      if (!data.success || data.notifications.length === 0) {
        listEl.innerHTML = `<div class="empty-state"><h3>No notifications</h3><p>You are all caught up!</p></div>`;
        return;
      }

      listEl.innerHTML = data.notifications.map(n => {
        const icon = n.type === 'MATCH_FOUND' ? '🤖' : (n.type.includes('CLAIM') ? '✋' : '📢');
        const unreadClass = !n.is_read ? 'unread' : '';

        return `
          <div class="notif-item ${unreadClass}" onclick="app.onNotificationClick(${n.id}, ${n.related_item_id || 'null'})">
            <div class="notif-header">
              <span class="notif-title">${icon} ${n.title}</span>
              <span class="notif-time">${n.created_at ? n.created_at.slice(0, 16) : ''}</span>
            </div>
            <p class="notif-msg">${n.message}</p>
          </div>
        `;
      }).join('');

    } catch (err) {
      listEl.innerHTML = `<div class="empty-state"><h3>Error loading alerts</h3></div>`;
    }
  }

  async onNotificationClick(notifId, relatedItemId) {
    await fetch(`/api/notifications/${notifId}/read`, { method: 'POST' });
    this.updateNotificationBadge();
    this.closeModal('notificationsModal');

    if (relatedItemId) {
      this.openItemDetails(relatedItemId);
    }
  }

  async markAllNotificationsRead() {
    try {
      await fetch('/api/notifications/read-all', { method: 'POST' });
      this.updateNotificationBadge();
      this.openNotificationsModal();
      this.showToast('All notifications marked as read', 'success');
    } catch (err) {
      this.showToast('Error marking notifications', 'error');
    }
  }

  // -------------------------------------------------------------
  // Modals & Toast Helper
  // -------------------------------------------------------------

  openModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.add('active');
  }

  closeModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.remove('active');
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
}

// Global Application Instance
document.addEventListener('DOMContentLoaded', () => {
  window.app = new CampusConnectApp();
});

<script>
	import { onMount, onDestroy } from 'svelte';

	let invoices = $state([]);
	let searchQuery = $state('');
	let isDragging = $state(false);
	let isUploading = $state(false);
	let uploadError = $state('');
	let isSyncingOneDrive = $state(false);
	let syncMessage = $state('');

	// Derived states
	let filteredInvoices = $derived(
		invoices.filter(inv => {
			const query = searchQuery.toLowerCase();
			return (
				(inv.filename?.toLowerCase() || '').includes(query) ||
				(inv.vendor?.toLowerCase() || '').includes(query) ||
				(inv.invoice_number?.toLowerCase() || '').includes(query)
			);
		})
	);

	let totalCount = $derived(invoices.length);
	let processingCount = $derived(invoices.filter(inv => inv.status === 'Ingesting' || inv.status === 'Pending').length);
	let processedCount = $derived(invoices.filter(inv => inv.status.startsWith('Processed')).length);
	let totalSpent = $derived(
		invoices
			.filter(inv => inv.status.startsWith('Processed') && inv.total_amount && inv.total_amount !== 'N/A')
			.reduce((sum, inv) => {
				// Clean amount formatting (strip currency symbols and commas)
				const cleaned = inv.total_amount.replace(/[^0-9.]/g, '');
				const val = parseFloat(cleaned);
				return isNaN(val) ? sum : sum + val;
			}, 0)
	);

	// Fetch invoice rows
	async function fetchInvoices() {
		try {
			const res = await fetch('http://localhost:8080/api/invoices');
			if (res.ok) {
				invoices = await res.json();
			}
		} catch (err) {
			console.error('Failed to fetch invoices:', err);
		}
	}

	// Upload handler
	async function uploadFile(file) {
		if (!file) return;
		if (file.type !== 'application/pdf') {
			uploadError = 'Only PDF invoice documents are supported';
			return;
		}
		
		isUploading = true;
		uploadError = '';
		
		const formData = new FormData();
		formData.append('file', file);
		
		try {
			const res = await fetch('http://localhost:8080/upload-invoice', {
				method: 'POST',
				body: formData
			});
			
			if (res.ok) {
				await fetchInvoices();
			} else {
				const errData = await res.json();
				uploadError = errData.detail || 'Failed to upload invoice file';
			}
		} catch (err) {
			uploadError = 'Unable to connect to FastAPI backend server';
		} finally {
			isUploading = false;
		}
	}

	function handleDrop(e) {
		e.preventDefault();
		isDragging = false;
		if (e.dataTransfer.files && e.dataTransfer.files[0]) {
			uploadFile(e.dataTransfer.files[0]);
		}
	}

	function handleFileChange(e) {
		if (e.target.files && e.target.files[0]) {
			uploadFile(e.target.files[0]);
		}
	}

	// Sync OneDrive handler
	async function forceSyncOneDrive() {
		isSyncingOneDrive = true;
		syncMessage = '';
		try {
			const res = await fetch('http://localhost:8080/api/sync-onedrive', {
				method: 'POST'
			});
			if (res.ok) {
				const data = await res.json();
				syncMessage = data.message;
				await fetchInvoices();
				// Clear status message after 4 seconds
				setTimeout(() => {
					syncMessage = '';
				}, 4000);
			} else {
				syncMessage = 'Sync triggering failed';
			}
		} catch (err) {
			syncMessage = 'Backend communication error';
		} finally {
			isSyncingOneDrive = false;
		}
	}

	// Formatter helper
	function formatUSD(val) {
		return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
	}

	// Live poll for state transitions
	let pollInterval;
	onMount(() => {
		fetchInvoices();
		// Poll every 3 seconds to update progress while files are processing
		pollInterval = setInterval(() => {
			const hasIngesting = invoices.some(inv => inv.status === 'Ingesting' || inv.status === 'Pending');
			if (hasIngesting || invoices.length === 0) {
				fetchInvoices();
			}
		}, 3000);
	});

	onDestroy(() => {
		if (pollInterval) clearInterval(pollInterval);
	});
</script>

<div class="dashboard-container">
	<!-- Top Bar -->
	<header class="top-bar">
		<div>
			<h2 class="page-title gradient-text">Invoice Intelligence Hub</h2>
			<p class="page-subtitle">Real-time structured extraction and vector index pipeline</p>
		</div>
		<div class="search-box">
			<span class="search-icon">🔍</span>
			<input type="text" placeholder="Search invoices by vendor, filename, or ID..." bind:value={searchQuery} />
		</div>
	</header>

	<!-- Metrics Grid -->
	<section class="metrics-grid">
		<div class="metric-card">
			<div class="metric-info">
				<p class="metric-label">Total Invoices</p>
				<h3 class="metric-value">{totalCount}</h3>
			</div>
			<div class="metric-icon">📂</div>
		</div>
		<div class="metric-card glow-card">
			<div class="metric-info">
				<p class="metric-label">Total Spent</p>
				<h3 class="metric-value gradient-text-accent">{formatUSD(totalSpent)}</h3>
			</div>
			<div class="metric-icon">💵</div>
		</div>
		<div class="metric-card">
			<div class="metric-info">
				<p class="metric-label">Processing / Pending</p>
				<h3 class="metric-value" class:active-pulse={processingCount > 0}>{processingCount}</h3>
			</div>
			<div class="metric-icon">⏳</div>
		</div>
		<div class="metric-card">
			<div class="metric-info">
				<p class="metric-label">Index Sync Rate</p>
				<h3 class="metric-value">{totalCount > 0 ? Math.round((processedCount / totalCount) * 100) : 0}%</h3>
			</div>
			<div class="metric-icon">⚡</div>
		</div>
	</section>

	<!-- Main Two-Column Layout -->
	<div class="dashboard-grid">
		<!-- Left Panel: Ingestion Zone -->
		<section class="panel-left">
			<div class="card panel-card">
				<h4 class="card-title">Manual Ingestion</h4>
				<p class="card-desc">Drag and drop a PDF invoice to instantly parse metadata and index into Chroma DB.</p>

				<!-- Drop Zone -->
				<label 
					class="upload-zone"
					class:dragging={isDragging}
					class:uploading={isUploading}
					ondragover={(e) => { e.preventDefault(); isDragging = true; }}
					ondragleave={() => isDragging = false}
					ondrop={handleDrop}
				>
					<input type="file" accept=".pdf" class="hidden-input" onchange={handleFileChange} disabled={isUploading} />
					{#if isUploading}
						<div class="spinner-container">
							<div class="spinner"></div>
							<p>Analyzing invoice structure...</p>
							<p class="subtext">Gemini & Flowise pipeline active</p>
						</div>
					{:else}
						<div class="upload-prompt">
							<span class="upload-icon">📥</span>
							<p class="upload-main-text">Drag invoice PDF here or <span class="highlight">browse</span></p>
							<p class="upload-sub-text">Supports standard PDF invoice templates</p>
						</div>
					{/if}
				</label>

				{#if uploadError}
					<div class="error-banner">
						<span class="error-icon">⚠️</span>
						<p>{uploadError}</p>
					</div>
				{/if}
			</div>

			<!-- OneDrive simulation panel -->
			<div class="card panel-card onedrive-card">
				<div class="onedrive-header">
					<div class="onedrive-title-group">
						<span class="onedrive-icon">☁️</span>
						<div>
							<h4 class="card-title">OneDrive Directory Watcher</h4>
							<span class="badge-status">Automated Monitor</span>
						</div>
					</div>
				</div>
				<p class="card-desc">FastAPI monitors this directory in the background. Dropping files in this path mimics automated email/OneDrive routing.</p>
				
				<div class="directory-path">
					<span class="path-icon">📁</span>
					<code>d:\InvoiceAI\mock_onedrive</code>
				</div>

				<div class="onedrive-actions">
					<button class="btn btn-secondary" onclick={forceSyncOneDrive} disabled={isSyncingOneDrive}>
						{#if isSyncingOneDrive}
							<div class="btn-spinner"></div>
							<span>Scanning folder...</span>
						{:else}
							<span>Sync Mock OneDrive</span>
						{/if}
					</button>
				</div>

				{#if syncMessage}
					<div class="sync-banner">
						<span class="sync-icon">✓</span>
						<p>{syncMessage}</p>
					</div>
				{/if}
			</div>
		</section>

		<!-- Right Panel: Data Table -->
		<section class="panel-right">
			<div class="card panel-card table-card">
				<div class="table-header">
					<h4 class="card-title">Ingested Invoice Repository</h4>
					<span class="count-badge">{filteredInvoices.length} entries</span>
				</div>

				<div class="table-wrapper">
					{#if filteredInvoices.length === 0}
						<div class="empty-state">
							<p>No invoices found.</p>
							<p class="empty-sub">Upload an invoice or trigger OneDrive synchronization.</p>
						</div>
					{:else}
						<table>
							<thead>
								<tr>
									<th>Document / Filename</th>
									<th>Invoice #</th>
									<th>Vendor</th>
									<th>Date</th>
									<th>Total Amount</th>
									<th>Sync Status</th>
								</tr>
							</thead>
							<tbody>
								{#each filteredInvoices as invoice (invoice.id)}
									<tr class="table-row">
										<td class="td-filename">
											<div class="file-cell">
												<span class="file-emoji">📄</span>
												<span class="filename-text" title={invoice.filename}>{invoice.filename}</span>
											</div>
										</td>
										<td><code>{invoice.invoice_number}</code></td>
										<td class="td-bold">{invoice.vendor}</td>
										<td>{invoice.date}</td>
										<td class="td-amount">{invoice.total_amount}</td>
										<td>
											<span class="status-badge" class:status-processed={invoice.status.startsWith('Processed')} class:status-ingesting={invoice.status === 'Ingesting'} class:status-failed={invoice.status.startsWith('Failed')}>
												{#if invoice.status === 'Ingesting'}
													<span class="status-dot-pulse"></span>
												{:else}
													<span class="status-dot"></span>
												{/if}
												{invoice.status}
											</span>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}
				</div>
			</div>
		</section>
	</div>
</div>

<style>
	.dashboard-container {
		padding: 32px;
		display: flex;
		flex-direction: column;
		gap: 32px;
		max-width: 1600px;
		margin: 0 auto;
		width: 100%;
	}

	.top-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 20px;
	}

	.page-title {
		font-size: 28px;
		font-weight: 700;
	}

	.page-subtitle {
		font-size: 14px;
		color: var(--text-muted);
		margin-top: 4px;
	}

	.search-box {
		position: relative;
		width: 380px;
		max-width: 100%;
	}

	.search-icon {
		position: absolute;
		left: 16px;
		top: 50%;
		transform: translateY(-50%);
		font-size: 16px;
		color: var(--text-muted);
	}

	.search-box input {
		width: 100%;
		background: var(--bg-surface);
		border: 1px solid var(--border-color);
		border-radius: 12px;
		padding: 12px 16px 12px 48px;
		color: var(--text-primary);
		font-family: var(--font-sans);
		font-size: 14px;
		transition: all var(--transition-normal);
		outline: none;
	}

	.search-box input:focus {
		border-color: var(--color-primary);
		box-shadow: var(--shadow-glow);
		background: var(--bg-surface-hover);
	}

	/* Metrics */
	.metrics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 20px;
	}

	.metric-card {
		background: var(--bg-card);
		border: 1px solid var(--border-color);
		border-radius: 16px;
		padding: 24px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		box-shadow: var(--shadow-sm);
		backdrop-filter: blur(8px);
		transition: transform var(--transition-fast), border-color var(--transition-fast);
	}

	.metric-card:hover {
		transform: translateY(-2px);
		border-color: rgba(255, 255, 255, 0.12);
	}

	.glow-card {
		border-color: var(--border-glow);
		box-shadow: var(--shadow-glow);
	}

	.metric-label {
		font-size: 13px;
		font-weight: 500;
		color: var(--text-muted);
	}

	.metric-value {
		font-family: var(--font-display);
		font-size: 26px;
		font-weight: 700;
		margin-top: 6px;
	}

	.active-pulse {
		animation: pulse-glow 2s infinite ease-in-out;
		color: var(--color-warning);
	}

	.metric-icon {
		font-size: 32px;
		background: rgba(255, 255, 255, 0.03);
		width: 54px;
		height: 54px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--border-color);
	}

	/* Layout Grid */
	.dashboard-grid {
		display: grid;
		grid-template-columns: 420px 1fr;
		gap: 24px;
		align-items: start;
	}

	@media (max-width: 1200px) {
		.dashboard-grid {
			grid-template-columns: 1fr;
		}
	}

	.panel-left {
		display: flex;
		flex-direction: column;
		gap: 24px;
	}

	.card {
		background: var(--bg-card);
		border: 1px solid var(--border-color);
		border-radius: 16px;
		padding: 24px;
		backdrop-filter: blur(8px);
		box-shadow: var(--shadow-md);
	}

	.card-title {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.card-desc {
		font-size: 13px;
		color: var(--text-muted);
		margin-top: 6px;
		margin-bottom: 20px;
		line-height: 1.5;
	}

	/* Upload Zone */
	.upload-zone {
		border: 2px dashed rgba(255, 255, 255, 0.1);
		border-radius: 12px;
		padding: 32px 16px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		cursor: pointer;
		transition: all var(--transition-normal);
		background: rgba(0, 0, 0, 0.1);
		position: relative;
	}

	.upload-zone:hover {
		border-color: var(--color-primary);
		background: rgba(99, 102, 241, 0.04);
	}

	.upload-zone.dragging {
		border-color: var(--color-primary);
		background: rgba(99, 102, 241, 0.08);
		transform: scale(0.99);
	}

	.hidden-input {
		display: none;
	}

	.upload-icon {
		font-size: 36px;
		margin-bottom: 12px;
		display: block;
	}

	.upload-main-text {
		font-size: 14px;
		font-weight: 500;
	}

	.upload-main-text .highlight {
		color: var(--color-primary);
		font-weight: 600;
		text-decoration: underline;
	}

	.upload-sub-text {
		font-size: 11px;
		color: var(--text-muted);
		margin-top: 6px;
	}

	/* Spinner */
	.spinner-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
	}

	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid rgba(255, 255, 255, 0.05);
		border-top-color: var(--color-primary);
		border-radius: 50%;
		animation: spin 1s infinite linear;
	}

	.spinner-container p {
		font-size: 14px;
		font-weight: 500;
		color: var(--text-primary);
	}

	.spinner-container .subtext {
		font-size: 11px;
		color: var(--text-muted);
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error-banner {
		margin-top: 16px;
		padding: 12px;
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.2);
		border-radius: 10px;
		display: flex;
		gap: 8px;
		align-items: flex-start;
	}

	.error-banner p {
		font-size: 12px;
		color: var(--color-danger);
	}

	/* OneDrive Panel */
	.onedrive-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 8px;
	}

	.onedrive-title-group {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.onedrive-icon {
		font-size: 24px;
	}

	.badge-status {
		font-size: 10px;
		font-weight: 600;
		color: var(--color-primary);
		background: rgba(99, 102, 241, 0.1);
		padding: 2px 8px;
		border-radius: 10px;
		border: 1px solid var(--border-glow);
		display: inline-block;
		margin-top: 4px;
	}

	.directory-path {
		background: rgba(0, 0, 0, 0.25);
		border: 1px solid var(--border-color);
		border-radius: 10px;
		padding: 12px;
		display: flex;
		align-items: center;
		gap: 10px;
		margin-bottom: 20px;
	}

	.path-icon {
		font-size: 16px;
	}

	.directory-path code {
		font-family: monospace;
		font-size: 12px;
		color: var(--text-secondary);
		word-break: break-all;
	}

	.onedrive-actions {
		display: flex;
	}

	.btn {
		background: var(--color-primary);
		color: #fff;
		border: none;
		border-radius: 10px;
		padding: 12px 20px;
		font-family: var(--font-sans);
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
		transition: all var(--transition-fast);
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		width: 100%;
	}

	.btn:hover:not(:disabled) {
		background: var(--color-primary-hover);
		box-shadow: var(--shadow-glow);
	}

	.btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-secondary {
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid var(--border-color);
		color: var(--text-primary);
	}

	.btn-secondary:hover:not(:disabled) {
		background: rgba(255, 255, 255, 0.08);
		border-color: rgba(255, 255, 255, 0.2);
	}

	.btn-spinner {
		width: 16px;
		height: 16px;
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-top-color: #fff;
		border-radius: 50%;
		animation: spin 0.6s infinite linear;
	}

	.sync-banner {
		margin-top: 16px;
		padding: 10px 14px;
		background: rgba(16, 185, 129, 0.08);
		border: 1px solid rgba(16, 185, 129, 0.2);
		border-radius: 10px;
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.sync-banner p {
		font-size: 12px;
		color: var(--color-success);
	}

	/* Data Table */
	.table-card {
		padding: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		min-height: 500px;
	}

	.table-header {
		padding: 24px;
		border-bottom: 1px solid var(--border-color);
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.count-badge {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--border-color);
		font-size: 11px;
		font-weight: 500;
		padding: 4px 10px;
		border-radius: 12px;
		color: var(--text-secondary);
	}

	.table-wrapper {
		overflow-x: auto;
		flex-grow: 1;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
		font-size: 13px;
	}

	th {
		background: rgba(0, 0, 0, 0.15);
		padding: 16px 24px;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		font-size: 10px;
		letter-spacing: 0.05em;
		border-bottom: 1px solid var(--border-color);
	}

	td {
		padding: 18px 24px;
		border-bottom: 1px solid var(--border-color);
		color: var(--text-secondary);
		vertical-align: middle;
	}

	.table-row {
		transition: background-color var(--transition-fast);
	}

	.table-row:hover {
		background: rgba(255, 255, 255, 0.015);
	}

	.td-bold {
		font-weight: 600;
		color: var(--text-primary);
	}

	.td-filename {
		max-width: 280px;
	}

	.file-cell {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.file-emoji {
		font-size: 16px;
	}

	.filename-text {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		display: block;
		font-weight: 500;
	}

	.td-amount {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--text-primary);
	}

	/* Status Badges */
	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 10px;
		border-radius: 12px;
		font-size: 11px;
		font-weight: 500;
		border: 1px solid transparent;
		white-space: nowrap;
	}

	.status-processed {
		background: rgba(16, 185, 129, 0.08);
		border-color: rgba(16, 185, 129, 0.2);
		color: var(--color-success);
	}

	.status-processed .status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--color-success);
		box-shadow: 0 0 6px var(--color-success);
	}

	.status-ingesting {
		background: rgba(245, 158, 11, 0.08);
		border-color: rgba(245, 158, 11, 0.2);
		color: var(--color-warning);
	}

	.status-ingesting .status-dot-pulse {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--color-warning);
		animation: pulse-dot 1.5s infinite ease-in-out;
	}

	.status-failed {
		background: rgba(239, 68, 68, 0.08);
		border-color: rgba(239, 68, 68, 0.2);
		color: var(--color-danger);
	}

	.status-failed .status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--color-danger);
	}

	@keyframes pulse-dot {
		0%, 100% {
			transform: scale(0.8);
			opacity: 0.5;
			box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4);
		}
		50% {
			transform: scale(1.2);
			opacity: 1;
			box-shadow: 0 0 0 4px rgba(245, 158, 11, 0);
		}
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 80px 24px;
		color: var(--text-muted);
		text-align: center;
		gap: 6px;
	}

	.empty-sub {
		font-size: 12px;
	}

	code {
		font-family: monospace;
		background: rgba(0, 0, 0, 0.2);
		padding: 2px 6px;
		border-radius: 4px;
		color: var(--text-secondary);
	}
</style>

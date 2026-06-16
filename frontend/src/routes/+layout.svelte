<script>
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state'; // Svelte 5 state matching

	let { children } = $props();

	// Function to check if a route is active
	function isActive(path) {
		if (path === '/') {
			return page.url.pathname === '/';
		}
		return page.url.pathname.startsWith(path);
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>InvoiceAI | Enterprise Finance Intelligence</title>
</svelte:head>

<div class="glow-mesh"></div>

<div class="app-container">
	<!-- Left Sidebar -->
	<aside class="sidebar">
		<div class="logo-area">
			<div class="logo-icon">
				<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3ZM19 19H5V5H19V19Z" fill="url(#logo-grad)"/>
					<path d="M17 12H7V14H17V12ZM17 8H7V10H17V8ZM13 16H7V18H13V16Z" fill="url(#logo-grad)"/>
					<defs>
						<linearGradient id="logo-grad" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
							<stop stop-color="var(--color-primary)"/>
							<stop offset="1" stop-color="var(--color-secondary)"/>
						</linearGradient>
					</defs>
				</svg>
			</div>
			<div class="logo-text">
				<h1>Invoice<span>AI</span></h1>
				<span class="logo-sub">Finance Intel</span>
			</div>
		</div>

		<nav class="nav-links">
			<a href="/" class="nav-item" class:active={isActive('/')}>
				<span class="nav-icon">📊</span>
				<span class="nav-label">Dashboard</span>
			</a>
			<a href="/chat" class="nav-item" class:active={isActive('/chat')}>
				<span class="nav-icon">💬</span>
				<span class="nav-label">Chat Assistant</span>
				<span class="badge">AI</span>
			</a>
		</nav>

		<div class="sidebar-footer">
			<div class="system-status">
				<div class="status-item">
					<span class="status-indicator online"></span>
					<div class="status-desc">
						<p class="status-title">FastAPI Backend</p>
						<p class="status-val">Active: Port 8080</p>
					</div>
				</div>
				<div class="status-item">
					<span class="status-indicator synced"></span>
					<div class="status-desc">
						<p class="status-title">Chroma Retriever</p>
						<p class="status-val">Local (Port 8000)</p>
					</div>
				</div>
			</div>
			<div class="user-profile">
				<div class="avatar">FN</div>
				<div class="user-info">
					<p class="user-name">Finance Team</p>
					<p class="user-role">Administrator</p>
				</div>
			</div>
		</div>
	</aside>

	<!-- Main View Content Area -->
	<main class="main-content">
		{@render children()}
	</main>
</div>

<style>
	.app-container {
		display: flex;
		width: 100vw;
		height: 100vh;
		overflow: hidden;
	}

	.sidebar {
		width: var(--sidebar-width);
		background: var(--bg-surface);
		backdrop-filter: blur(16px);
		border-right: 1px solid var(--border-color);
		display: flex;
		flex-direction: column;
		padding: 24px 16px;
		flex-shrink: 0;
	}

	.logo-area {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px;
		margin-bottom: 32px;
	}

	.logo-icon {
		width: 38px;
		height: 38px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.logo-icon svg {
		width: 100%;
		height: 100%;
	}

	.logo-text h1 {
		font-family: var(--font-display);
		font-size: 20px;
		font-weight: 700;
		letter-spacing: -0.03em;
		color: var(--text-primary);
		line-height: 1;
	}

	.logo-text h1 span {
		color: var(--color-primary);
		background: linear-gradient(135deg, var(--color-primary) 30%, var(--color-secondary) 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
	}

	.logo-sub {
		font-size: 11px;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		font-weight: 600;
	}

	.nav-links {
		display: flex;
		flex-direction: column;
		gap: 8px;
		flex-grow: 1;
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: 14px;
		padding: 12px 16px;
		border-radius: 10px;
		color: var(--text-secondary);
		font-size: 14px;
		font-weight: 500;
		transition: all var(--transition-fast);
		border: 1px solid transparent;
		position: relative;
	}

	.nav-item:hover {
		color: var(--text-primary);
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid rgba(255, 255, 255, 0.05);
	}

	.nav-item.active {
		color: var(--text-primary);
		background: linear-gradient(90deg, rgba(132, 176, 193, 0.15) 0%, rgba(51, 74, 117, 0.05) 100%);
		border: 1px solid var(--border-glow);
		box-shadow: var(--shadow-sm);
	}

	.nav-item.active::before {
		content: '';
		position: absolute;
		left: 0;
		top: 15%;
		height: 70%;
		width: 3px;
		background: var(--color-primary);
		border-radius: 0 4px 4px 0;
	}

	.nav-icon {
		font-size: 18px;
	}

	.badge {
		margin-left: auto;
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
		font-size: 10px;
		font-weight: 700;
		padding: 2px 6px;
		border-radius: 12px;
		color: #fff;
		box-shadow: 0 0 10px rgba(132, 176, 193, 0.3);
	}

	.sidebar-footer {
		margin-top: auto;
		display: flex;
		flex-direction: column;
		gap: 20px;
		border-top: 1px solid var(--border-color);
		padding-top: 20px;
	}

	.system-status {
		display: flex;
		flex-direction: column;
		gap: 12px;
		background: rgba(255, 255, 255, 0.01);
		border: 1px solid var(--border-color);
		padding: 12px;
		border-radius: 10px;
	}

	.status-item {
		display: flex;
		align-items: flex-start;
		gap: 10px;
	}

	.status-indicator {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		margin-top: 4px;
		flex-shrink: 0;
	}

	.status-indicator.online {
		background-color: var(--color-success);
		box-shadow: 0 0 8px var(--color-success);
	}

	.status-indicator.synced {
		background-color: var(--color-primary);
		box-shadow: 0 0 8px var(--color-primary);
	}

	.status-desc {
		display: flex;
		flex-direction: column;
	}

	.status-title {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.status-val {
		font-size: 10px;
		color: var(--text-muted);
	}

	.user-profile {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.avatar {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 12px;
		font-weight: 700;
		color: #fff;
		border: 1px solid rgba(255, 255, 255, 0.15);
	}

	.user-info {
		display: flex;
		flex-direction: column;
	}

	.user-name {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.user-role {
		font-size: 11px;
		color: var(--text-muted);
	}

	.main-content {
		flex-grow: 1;
		height: 100%;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		background: radial-gradient(circle at 50% -20%, rgba(132, 176, 193, 0.04) 0%, transparent 70%);
	}

	@media (max-width: 768px) {
		.app-container {
			flex-direction: column;
		}
		.sidebar {
			width: 100%;
			height: auto;
			border-right: none;
			border-bottom: 1px solid var(--border-color);
			padding: 16px;
		}
		.logo-area {
			margin-bottom: 16px;
		}
		.nav-links {
			flex-direction: row;
			flex-wrap: wrap;
			margin-bottom: 0;
		}
		.sidebar-footer {
			display: none;
		}
	}
</style>

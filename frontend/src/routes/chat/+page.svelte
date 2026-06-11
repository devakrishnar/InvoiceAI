<script>
	import { onMount, tick } from 'svelte';

	let question = $state('');
	let isSending = $state(false);
	let chatContainer = $state(null);

	let messages = $state([
		{
			sender: 'ai',
			text: 'Hello! I am your Invoice Intelligence assistant. Ask me anything about the ingested invoices, total spend, vendors, or invoice numbers.'
		}
	]);

	const quickPrompts = [
		'What is our total spent?',
		'List all vendors in the database',
		'Find the highest invoice amount',
		'Show invoice totals by vendor'
	];

	async function scrollToBottom() {
		await tick();
		if (chatContainer) {
			chatContainer.scrollTo({
				top: chatContainer.scrollHeight,
				behavior: 'smooth'
			});
		}
	}

	async function handleSend(customText = '') {
		const textToSend = (customText || question).trim();
		if (!textToSend || isSending) return;

		if (!customText) {
			question = '';
		}

		// Push User Message
		messages.push({
			sender: 'user',
			text: textToSend
		});
		await scrollToBottom();

		isSending = true;

		try {
			const res = await fetch('http://localhost:8080/api/chat', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					question: textToSend,
					history: messages.map(m => ({
						type: m.sender === 'user' ? 'userMessage' : 'apiMessage',
						message: m.text
					})).slice(0, -1) // Exclude the message we just added
				})
			});

			if (res.ok) {
				const data = await res.json();
				// Flowise can output 'text', 'output', etc. FastAPI returns {'text': ...}
				const reply = data.text || data.output || 'No response returned from the AI model.';
				messages.push({
					sender: 'ai',
					text: reply
				});
			} else {
				const errorTxt = await res.text();
				messages.push({
					sender: 'ai',
					text: `Failed to query the AI assistant. Server responded with: ${errorTxt || 'Unknown server error'}`
				});
			}
		} catch (err) {
			messages.push({
				sender: 'ai',
				text: 'Backend communication error. Please ensure the FastAPI server is running on http://localhost:8080.'
			});
		} finally {
			isSending = false;
			await scrollToBottom();
		}
	}

	onMount(() => {
		scrollToBottom();
	});
</script>

<div class="chat-page-container">
	<!-- Chat Header -->
	<header class="chat-header">
		<div class="header-main">
			<div class="copilot-avatar">🤖</div>
			<div>
				<h2 class="chat-title">Finance AI Copilot</h2>
				<div class="copilot-status">
					<span class="pulse-green"></span>
					<span class="status-text">Ready for Queries</span>
				</div>
			</div>
		</div>
		<div class="pipeline-badge">
			<span class="badge-text">RAG Retriever Active</span>
		</div>
	</header>

	<!-- Chat Area -->
	<div class="chat-scroller" bind:this={chatContainer}>
		<div class="messages-list">
			{#each messages as msg}
				<div class="message-wrapper" class:user-msg={msg.sender === 'user'}>
					{#if msg.sender === 'ai'}
						<div class="chat-avatar">AI</div>
					{/if}
					<div class="message-bubble" class:user-bubble={msg.sender === 'user'}>
						<div class="message-text">
							{#each msg.text.split('\n') as line}
								<p>{line}</p>
							{/each}
						</div>
					</div>
				</div>
			{/each}

			<!-- Loading State -->
			{#if isSending}
				<div class="message-wrapper">
					<div class="chat-avatar shimmer-bg">AI</div>
					<div class="message-bubble loading-bubble">
						<div class="bouncing-dots">
							<span class="dot"></span>
							<span class="dot"></span>
							<span class="dot"></span>
						</div>
						<div class="skeleton-line shimmer-bg"></div>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!-- Suggestions Bar -->
	{#if messages.length <= 2 && !isSending}
		<div class="quick-prompts-bar">
			<p class="quick-title">Quick Prompts:</p>
			<div class="prompts-list">
				{#each quickPrompts as prompt}
					<button class="prompt-btn" onclick={() => handleSend(prompt)}>
						{prompt}
					</button>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Input Area -->
	<footer class="chat-input-area">
		<form class="input-form" onsubmit={(e) => { e.preventDefault(); handleSend(); }}>
			<input 
				type="text" 
				placeholder="Ask about invoices, sums, dates, or vendors..." 
				bind:value={question} 
				disabled={isSending} 
			/>
			<button type="submit" class="send-btn" disabled={!question.trim() || isSending}>
				<span class="btn-text">Send</span>
				<span class="btn-arrow">➔</span>
			</button>
		</form>
	</footer>
</div>

<style>
	.chat-page-container {
		display: flex;
		flex-direction: column;
		height: 100vh;
		width: 100%;
		max-width: 1200px;
		margin: 0 auto;
		background: rgba(16, 18, 35, 0.4);
		border-left: 1px solid var(--border-color);
		border-right: 1px solid var(--border-color);
	}

	.chat-header {
		padding: 24px;
		border-bottom: 1px solid var(--border-color);
		display: flex;
		justify-content: space-between;
		align-items: center;
		background: rgba(16, 18, 35, 0.7);
		backdrop-filter: blur(8px);
	}

	.header-main {
		display: flex;
		align-items: center;
		gap: 16px;
	}

	.copilot-avatar {
		font-size: 28px;
		background: rgba(99, 102, 241, 0.1);
		width: 50px;
		height: 50px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--border-glow);
	}

	.chat-title {
		font-size: 18px;
		font-weight: 700;
	}

	.copilot-status {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 4px;
	}

	.pulse-green {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background-color: var(--color-success);
		box-shadow: 0 0 8px var(--color-success);
		animation: status-pulse 2s infinite ease-in-out;
	}

	@keyframes status-pulse {
		0%, 100% { opacity: 0.6; }
		50% { opacity: 1; }
	}

	.status-text {
		font-size: 11px;
		color: var(--text-muted);
		font-weight: 500;
	}

	.pipeline-badge {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--border-color);
		padding: 6px 12px;
		border-radius: 20px;
	}

	.badge-text {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
	}

	/* Chat Scroller */
	.chat-scroller {
		flex-grow: 1;
		overflow-y: auto;
		padding: 24px;
		display: flex;
		flex-direction: column;
	}

	.messages-list {
		display: flex;
		flex-direction: column;
		gap: 20px;
		max-width: 900px;
		width: 100%;
		margin: 0 auto;
		margin-top: auto; /* Push content to bottom if it is short */
	}

	.message-wrapper {
		display: flex;
		gap: 16px;
		align-items: flex-start;
		animation: message-slide-in 0.3s cubic-bezier(0.16, 1, 0.3, 1);
	}

	@keyframes message-slide-in {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.user-msg {
		flex-direction: row-reverse;
	}

	.chat-avatar {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: rgba(99, 102, 241, 0.15);
		border: 1px solid var(--border-glow);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 11px;
		font-weight: 700;
		color: var(--color-primary);
		flex-shrink: 0;
	}

	.message-bubble {
		background: var(--bg-card);
		border: 1px solid var(--border-color);
		padding: 16px;
		border-radius: 0 16px 16px 16px;
		max-width: 75%;
		box-shadow: var(--shadow-sm);
	}

	.user-bubble {
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
		border: none;
		border-radius: 16px 0 16px 16px;
		color: #fff;
		box-shadow: var(--shadow-glow);
	}

	.message-text p {
		font-size: 14px;
		line-height: 1.6;
		margin-bottom: 8px;
		color: inherit;
	}

	.message-text p:last-child {
		margin-bottom: 0;
	}

	.user-bubble .message-text p {
		color: rgba(255, 255, 255, 0.95);
	}

	/* Loading Indicator */
	.loading-bubble {
		display: flex;
		flex-direction: column;
		gap: 10px;
		min-width: 140px;
	}

	.bouncing-dots {
		display: flex;
		gap: 6px;
		align-items: center;
	}

	.bouncing-dots .dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background-color: var(--color-primary);
		animation: dot-bounce 1.4s infinite ease-in-out both;
	}

	.bouncing-dots .dot:nth-child(1) { animation-delay: -0.32s; }
	.bouncing-dots .dot:nth-child(2) { animation-delay: -0.16s; }

	@keyframes dot-bounce {
		0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
		40% { transform: scale(1.1); opacity: 1; }
	}

	.skeleton-line {
		height: 8px;
		width: 100%;
		border-radius: 4px;
	}

	/* Prompts */
	.quick-prompts-bar {
		padding: 12px 24px;
		max-width: 900px;
		width: 100%;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.quick-title {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-muted);
	}

	.prompts-list {
		display: flex;
		gap: 10px;
		flex-wrap: wrap;
	}

	.prompt-btn {
		background: rgba(255, 255, 255, 0.02);
		border: 1px solid var(--border-color);
		color: var(--text-secondary);
		padding: 8px 16px;
		border-radius: 18px;
		font-family: var(--font-sans);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.prompt-btn:hover {
		color: var(--text-primary);
		background: rgba(99, 102, 241, 0.06);
		border-color: var(--border-glow);
		box-shadow: var(--shadow-sm);
		transform: translateY(-1px);
	}

	/* Input Footer */
	.chat-input-area {
		padding: 24px;
		border-top: 1px solid var(--border-color);
		background: rgba(16, 18, 35, 0.8);
		backdrop-filter: blur(8px);
	}

	.input-form {
		max-width: 900px;
		width: 100%;
		margin: 0 auto;
		display: flex;
		gap: 12px;
		position: relative;
	}

	.input-form input {
		flex-grow: 1;
		background: var(--bg-surface);
		border: 1px solid var(--border-color);
		padding: 16px 20px;
		border-radius: 12px;
		color: var(--text-primary);
		font-family: var(--font-sans);
		font-size: 14px;
		outline: none;
		transition: all var(--transition-normal);
	}

	.input-form input:focus {
		border-color: var(--color-primary);
		background: var(--bg-surface-hover);
		box-shadow: var(--shadow-glow);
	}

	.send-btn {
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
		border: none;
		color: #fff;
		padding: 0 24px;
		border-radius: 12px;
		font-family: var(--font-sans);
		font-size: 14px;
		font-weight: 600;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		gap: 8px;
		transition: all var(--transition-fast);
		box-shadow: var(--shadow-glow);
	}

	.send-btn:hover:not(:disabled) {
		opacity: 0.95;
		transform: translateY(-1px);
	}

	.send-btn:disabled {
		background: rgba(255, 255, 255, 0.05);
		color: var(--text-muted);
		cursor: not-allowed;
		box-shadow: none;
		border: 1px solid var(--border-color);
	}

	.btn-arrow {
		transition: transform var(--transition-fast);
	}

	.send-btn:hover:not(:disabled) .btn-arrow {
		transform: translateX(2px);
	}
</style>

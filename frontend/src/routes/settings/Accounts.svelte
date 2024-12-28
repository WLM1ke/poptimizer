<script lang="ts">
	import H2 from "$lib/components/H2.svelte";
	import Delete from "$lib/icons/Delete.svelte";
	import Add from "$lib/icons/Add.svelte";
	import { scale } from "svelte/transition";
	import Switch from "$lib/components/Switch.svelte";
	import { flip } from "svelte/animate";
	import { portfolio } from "$lib/state/portfolio.svelte";
	import { accHideZeroPositions, accSortByValue } from "$lib/state/settings.svelte";

	let newAccount = $state();
	let inputRef: HTMLElement;
</script>

<section>
	<H2 text="Accounts" />
	<ul class="max-w-max">
		{#each portfolio.accounts as account (account)}
			<li transition:scale animate:flip class="flex items-center justify-between gap-2 pt-2">
				{account}
				<button onclick={() => portfolio.removeAccount(account)} class="hover:text-link-hover">
					<Delete />
				</button>
			</li>
		{/each}
		<li class="flex items-center justify-between gap-2 pt-2">
			<input
				bind:this={inputRef}
				onkeydown={(event) => {
					if (event.key === "Enter") {
						portfolio.createAccount(newAccount);
						newAccount = "";
					}
				}}
				class="border-bg-accent bg-bg-main rounded-md border p-1"
				bind:value={newAccount}
				type="text"
				placeholder="Enter account title"
			/>
			<button
				onclick={() => {
					portfolio.createAccount(newAccount);
					inputRef.focus();
					newAccount = "";
				}}
				class="hover:text-link-hover"
			>
				<Add />
			</button>
		</li>
	</ul>
	<ul class="pt-2">
		<li>
			<Switch label="sort value descending" checked={accSortByValue.get()} onchange={accSortByValue.toggle} />
		</li>
		<li>
			<Switch label="hide zero positions" checked={accHideZeroPositions.get()} onchange={accHideZeroPositions.toggle} />
		</li>
	</ul>
</section>

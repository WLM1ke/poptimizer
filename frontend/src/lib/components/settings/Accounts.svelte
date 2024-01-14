<script lang="ts">
	import H2 from "$lib/components/base/H2.svelte";
	import { accounts, removeAccount, createAccount } from "$lib/stores/portfolio";
	import Delete from "$lib/icons/Delete.svelte";
	import Add from "$lib/icons/Add.svelte";
	import { scale } from "svelte/transition";
	import Switch from "$lib/components/base/Switch.svelte";
	import { settings } from "$lib/stores/settings";

	let newAccount = "";
	let inputRef: HTMLElement;

	const onCreateAccount = () => {
		inputRef.focus();
	};
</script>

<section>
	<H2>Accounts</H2>
	<ul class="max-w-max">
		{#each $accounts as account (account)}
			<li transition:scale class="flex items-center justify-between gap-2 pt-2">
				{account}
				<button on:click={() => removeAccount(account)} class="hover:text-link">
					<Delete />
				</button>
			</li>
		{/each}
		<li class="flex items-center justify-between gap-2 pt-2">
			<input
				bind:this={inputRef}
				on:keydown={(event) => {
					if (event.key === "Enter") {
						createAccount(newAccount);
						newAccount = "";
					}
				}}
				class="border-bg-accent bg-bg-main rounded-md border p-1"
				bind:value={newAccount}
				type="text"
				placeholder="Enter account title"
			/>
			<button
				on:click={() => {
					createAccount(newAccount);
					onCreateAccount();
					newAccount = "";
				}}
				class="hover:text-link"
			>
				<Add />
			</button>
		</li>
	</ul>
	<ul class="pt-2">
		<li>
			<Switch
				label="sort value ascending"
				checked={$settings.accounts.sortByValue}
				on:change={() => {
					settings.update((settings) => {
						settings.accounts.sortByValue = !settings.accounts.sortByValue;

						return settings;
					});
				}}
			/>
		</li>
		<li>
			<Switch
				label="hide zero positions"
				checked={$settings.accounts.hideZeroPositions}
				on:change={() => {
					settings.update((settings) => {
						settings.accounts.hideZeroPositions = !settings.accounts.hideZeroPositions;

						return settings;
					});
				}}
			/>
		</li>
	</ul>
</section>

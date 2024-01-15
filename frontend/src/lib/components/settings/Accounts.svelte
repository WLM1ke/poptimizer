<script lang="ts">
	import H2 from "$lib/components/base/H2.svelte";
	import { accounts, removeAccount, createAccount } from "$lib/stores/portfolio";
	import Delete from "$lib/icons/Delete.svelte";
	import Add from "$lib/icons/Add.svelte";
	import { scale } from "svelte/transition";
	import Switch from "$lib/components/base/Switch.svelte";
	import {
		accountsSortByValue,
		toggleAccountsSortByValue,
		accountsHideZeroPositions,
		toggleAccountsHideZeroPositions
	} from "$lib/stores/settings";

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
				class="rounded-md border border-bg-accent bg-bg-main p-1"
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
			<Switch label="sort value descending" checked={$accountsSortByValue} on:change={toggleAccountsSortByValue} />
		</li>
		<li>
			<Switch
				label="hide zero positions"
				checked={$accountsHideZeroPositions}
				on:change={toggleAccountsHideZeroPositions}
			/>
		</li>
	</ul>
</section>

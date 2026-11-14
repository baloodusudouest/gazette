<script>
  // Les autres possibilités pour un bloc, avec leur date, leur portée et le drapeau « sensible ».
  import TriangleAlert from '@lucide/svelte/icons/triangle-alert'
  import { dateCourte, PORTEES } from '$lib/format.js'
  let { liste = [], choisis = [], onchoisir, onfermer } = $props()
  let filtre = $state('')
  let voirSensibles = $state(false)
  const visibles = $derived(liste.filter((f) => (voirSensibles || !f.sensible?.length)
    && (!filtre || (f.texte + ' ' + f.rubrique).toLowerCase().includes(filtre.toLowerCase()))))
  const nbSensibles = $derived(liste.filter((f) => f.sensible?.length).length)
</script>

<div class="mt-3 rounded-xl border bg-background p-3">
  <div class="mb-2 flex flex-wrap items-center gap-2">
    <input bind:value={filtre} placeholder="Chercher…" class="h-9 flex-1 rounded-lg border bg-card px-3 text-sm" />
    {#if nbSensibles}
      <label class="flex items-center gap-1.5 text-xs text-muted-foreground">
        <input type="checkbox" bind:checked={voirSensibles} /> voir les {nbSensibles} sensibles
      </label>
    {/if}
    <button type="button" class="text-xs text-muted-foreground underline" onclick={onfermer}>fermer</button>
  </div>
  <ul class="grid max-h-80 gap-1 overflow-y-auto">
    {#each visibles as f (f.id)}
      <li>
        <button type="button" onclick={() => onchoisir(f)} disabled={choisis.includes(f.id)}
                class="w-full rounded-lg px-2 py-1.5 text-left text-sm hover:bg-secondary disabled:opacity-40">
          <span class="text-xs text-muted-foreground">{dateCourte(f.date)} · {PORTEES[f.portee] ?? f.portee}
            {#if f.source === 'larousse'} · Larousse{/if}{#if f.langue === 'en'} · <b class="text-primary">en anglais, à traduire</b>{/if}</span>
          {#if f.sensible?.length}
            <span class="ml-1 inline-flex items-center gap-1 text-xs text-destructive"><TriangleAlert class="size-3" aria-hidden="true" />sensible : {f.sensible.join(', ')}</span>
          {/if}
          <span class="block">{#if f.rubrique}<b>{f.rubrique}.</b> {/if}{f.texte}</span>
        </button>
      </li>
    {:else}
      <li class="px-2 py-1.5 text-sm text-muted-foreground">Rien d'autre.</li>
    {/each}
  </ul>
</div>

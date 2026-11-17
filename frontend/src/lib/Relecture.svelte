<script>
  // 0.17 : bandeau de la relecture (Gazette et Récidive) — ce qui reste à valider, la file de l'IA, « Revoir tout »,
  // et quand tout est validé, le gros bouton Approuver seul.
  import { Button } from '$lib/components/ui/button/index.js'
  import { fileIa } from '$lib/fileIa.svelte.js'

  let { restants, total, revoir = $bindable(false), approuver, attente = '', etat = '', modifie = false, journal = 'le journal' } = $props()
  const fini = $derived(total > 0 && restants === 0)
</script>

{#if fini && !revoir}
  <div class="grid justify-items-center gap-4 rounded-2xl border border-valide/60 bg-card px-4 py-10 text-center">
    <p class="text-lg font-medium">Tout est validé.</p>
    <Button size="lg" class="h-14 px-10 text-lg" onclick={approuver} disabled={attente !== '' || etat === 'approuve' && !modifie}>
      {attente === 'approuver' ? 'Contrôle…' : etat === 'approuve' && !modifie ? 'Approuvé' : `Approuver ${journal}`}</Button>
    <button type="button" class="text-sm text-muted-foreground underline hover:text-foreground" onclick={() => (revoir = true)}>Revoir les éléments validés</button>
  </div>
{:else}
  <div class="flex flex-wrap items-center justify-between gap-2 rounded-xl border px-3 py-2 text-sm" role="status">
    <span>{total ? `${restants} élément${restants > 1 ? 's' : ''} à valider sur ${total}` : 'Rien à valider'}
      {#if fileIa.enCours}<span class="text-muted-foreground"> · IA : {fileIa.enCours}{fileIa.attente.length ? `, puis ${fileIa.attente.length} en file` : ''}</span>{/if}</span>
    <label class="flex items-center gap-2 text-xs text-muted-foreground"><input type="checkbox" bind:checked={revoir} /> Montrer aussi les validés</label>
  </div>
{/if}

<script>
  // 0.12 : aides de l'IA du PC pour un bloc de la Gazette classique (titres, raccourcir, version journal, traduire,
  // mot des hôtes). Des propositions à choisir : un toucher les applique au bloc ; rien n'est enregistré sans Julien.
  import Sparkles from '@lucide/svelte/icons/sparkles'
  import { api } from '$lib/api.js'

  let { pid, texte, actions, signes = null, onapply } = $props()
  const NOMS = { titres: 'Titres', raccourcir: 'Raccourcir', journal: 'Version journal', traduire: 'Traduire', mot: '3 mots' }
  let props = $state([])
  let derniere = $state('')
  let attente = $state('')
  let erreur = $state('')

  async function demander(action) {
    attente = action
    erreur = ''
    props = []
    try {
      props = (await api.post(`/api/livrets/${pid}/ia`, { action, texte: texte(), signes: action === 'raccourcir' ? signes : null })).propositions
      derniere = action
    } catch (err) { erreur = err.message }
    attente = ''
  }
</script>

<div class="mt-1 grid min-w-0 gap-1">
  <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
    <Sparkles class="size-3.5" aria-hidden="true" /><span class="sr-only">IA :</span>
    {#each actions as a}
      <button type="button" class="hover:text-foreground disabled:opacity-50" disabled={attente !== ''} onclick={() => demander(a)}>
        {attente === a ? '…' : NOMS[a]}</button>
    {/each}
  </div>
  {#if erreur}<p class="text-xs text-destructive">{erreur}</p>{/if}
  {#if props.length}
    <ul class="grid gap-1 rounded-lg border border-dashed p-1.5" aria-label="Propositions de l'IA">
      {#each props as t}
        <li><button type="button" class="w-full rounded-md px-2 py-1 text-left text-sm break-words whitespace-pre-line hover:bg-secondary"
                    onclick={() => { onapply(derniere, t); props = [] }}>{t}</button></li>
      {/each}
      <li><button type="button" class="px-2 text-xs text-muted-foreground hover:text-foreground" onclick={() => (props = [])}>Fermer</button></li>
    </ul>
  {/if}
</div>

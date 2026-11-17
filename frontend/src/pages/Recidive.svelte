<script>
  // 0.9 : une édition de La Récidive (journal à scandale, à partir du 2e séjour) — relecture à gauche (N°, accroche,
  // photos et légendes, retrait, mot des hôtes), aperçu des 4 pages à droite. « Approuver » contrôle d'abord
  // qu'aucune page ne déborde. Rien ne s'imprime sans approbation. Légendes de gabarit en 0.9 (pas d'IA).
  import { onMount, onDestroy } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import Download from '@lucide/svelte/icons/download'
  import EyeOff from '@lucide/svelte/icons/eye-off'
  import Eye from '@lucide/svelte/icons/eye'
  import RefreshCw from '@lucide/svelte/icons/refresh-cw'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Etat from '$lib/Etat.svelte'
  import { dateCourte, dateLongue } from '$lib/format.js'

  let { id, onchange, ondeconnecte } = $props()
  let d = $state(null)
  let photos = $state([])
  let mot = $state('')
  let accroche = $state('')
  let numero = $state('')
  let modifie = $state(false)
  let message = $state('')
  let attente = $state('')
  let tampon = $state(Date.now())
  let largeur = $state(400)
  let minuteur = null

  async function lire() {
    try {
      d = await api.get(`/api/recidives/${id}`)
      const ed = d.edition
      photos = ed.photos.map((p) => ({ ...p }))
      mot = ed.mot || ed.mot_defaut
      accroche = ed.accroche || ed.accroche_defaut
      numero = ed.numero_main ?? ''
      modifie = false
      tampon = Date.now()
      clearTimeout(minuteur)
      if (ed.etat === 'en_preparation') minuteur = setTimeout(lire, 3000)
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      else message = err.message
    }
  }
  function toucher() { modifie = true; message = '' }
  const corps = () => ({ numero_main: numero === '' ? null : +numero, accroche, mot,
                         photos: photos.map((p) => ({ id: p.id, legende: p.legende, retiree: p.retiree })) })
  async function enregistrer() {
    attente = 'enregistrer'
    try { await api.put(`/api/recidives/${id}`, corps()); await lire(); message = 'Enregistré.'; onchange?.() }
    catch (err) { message = err.message }
    attente = ''
  }
  async function approuver() {
    if (modifie) await enregistrer()
    attente = 'approuver'
    try { await api.post(`/api/recidives/${id}/approuver`); await lire(); message = 'Édition approuvée : prête à imprimer.'; onchange?.() }
    catch (err) { message = err.message }
    attente = ''
  }
  async function preparer(completer) {
    if (!completer && !confirm('Refaire le choix des photos depuis Immich ? Les légendes écrites sont perdues ; le mot, l\'accroche et le N° corrigé sont gardés.')) return
    if (modifie) await api.put(`/api/recidives/${id}`, corps())
    await api.post(`/api/recidives/${id}/preparer`, { completer })
    await lire()
  }
  function basculer(p) { p.retiree = !p.retiree; toucher() }
  const vues = $derived(photos.filter((p) => !p.retiree))
  const echelle = $derived(Math.min(1, largeur / 600))
  const ed = $derived(d?.edition)
  onMount(lire)
  onDestroy(() => clearTimeout(minuteur))
</script>

{#if d}
  <header class="mb-5 flex flex-wrap items-end justify-between gap-3">
    <div>
      <a href="#/livrets" class="mb-1 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft class="size-4" aria-hidden="true" />Livrets</a>
      <p class="etiquette">La Récidive · N° {ed.numero_main ?? ed.numero}</p>
      <h1 class="titre flex flex-wrap items-center gap-3">{d.personne.nom} <Etat etat={ed.etat} /></h1>
      <p class="mt-1 text-sm text-muted-foreground">Séjour du {dateLongue(ed.sejour_du)}
        {#if ed.precedent} · photos depuis le {dateLongue(ed.precedent.du)}{/if}
        · {ed.trouvees} photo{ed.trouvees > 1 ? 's' : ''} trouvée{ed.trouvees > 1 ? 's' : ''} dans Immich</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <Button variant="outline" onclick={enregistrer} disabled={!modifie || attente !== ''}>{attente === 'enregistrer' ? 'Enregistrement…' : 'Enregistrer'}</Button>
      <Button onclick={approuver} disabled={attente !== '' || !['a_relire', 'approuve'].includes(ed.etat) || ed.etat === 'approuve' && !modifie}>
        {attente === 'approuver' ? 'Contrôle…' : ed.etat === 'approuve' && !modifie ? 'Approuvée' : 'Approuver'}</Button>
    </div>
  </header>

  {#if message}<p class="mb-4 rounded-xl border px-4 py-2 text-sm" role="status">{message}</p>{/if}
  {#if ed.erreur}<p class="mb-4 rounded-xl border border-destructive/60 px-4 py-2 text-sm text-destructive" role="alert">{ed.erreur}</p>{/if}
  {#if ed.etat === 'vide'}
    <p class="mb-4 rounded-xl border px-4 py-2 text-sm">Aucune photo de {d.personne.prenom || d.personne.nom} depuis le séjour précédent : ce séjour garde la <a class="underline" href={'#/livret/' + d.personne.id}>Gazette</a>.</p>
  {/if}
  {#if ed.manque_scandale && ed.etat === 'a_relire'}
    <p class="mb-4 rounded-xl border border-primary/50 px-4 py-2 text-sm">{vues.length} photo{vues.length > 1 ? 's' : ''} sur {d.places} :
      {ed.tag_absent ? 'le tag « scandale » n\'existe pas encore dans Immich.' : 'aucune photo de la personne avec le tag « scandale » dans Immich.'}
      Tague quelques vieilles photos, puis « Compléter ».</p>
  {/if}

  <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
    <div class="grid min-w-0 content-start gap-4">
      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Une">
        <h2 class="etiquette mb-2">Page 1 · la une</h2>
        <div class="grid gap-3 sm:grid-cols-[8rem_minmax(0,1fr)]">
          <label class="grid gap-1 text-sm"><span class="etiquette">N° (corrigé)</span>
            <input type="number" min="2" max="99" placeholder={String(ed.numero)} class="rounded-lg border bg-background px-2 py-1" bind:value={numero} oninput={toucher} /></label>
          <label class="grid gap-1 text-sm"><span class="etiquette">Accroche sous le titre</span>
            <input class="rounded-lg border bg-background px-2 py-1" maxlength="80" bind:value={accroche} oninput={toucher} /></label>
        </div>
        <p class="mt-1 text-xs text-muted-foreground">N° vide : celui du séjour ({ed.numero}). Accroche proposée d'après le genre de la fiche carnet : « {ed.accroche_defaut} ».</p>
      </section>

      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Photos">
        <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2 class="etiquette">Les preuves · {vues.length} photo{vues.length > 1 ? 's' : ''} sur {d.places}</h2>
          <span class="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onclick={() => preparer(true)} disabled={ed.etat === 'en_preparation'}><RefreshCw class="size-3.5" aria-hidden="true" />Compléter</Button>
            <Button size="sm" variant="ghost" onclick={() => preparer(false)} disabled={ed.etat === 'en_preparation'}>Tout refaire</Button>
          </span>
        </div>
        <p class="mb-3 text-xs text-muted-foreground">La première photo fait la une. « Retirer » écarte une photo (elle ne reviendra pas) ; « Compléter » cherche de quoi remplir les places libres.</p>
        <ul class="grid gap-3 sm:grid-cols-2">
          {#each photos as p, i (p.id)}
            <li class="flex min-w-0 flex-col gap-2 rounded-xl border p-2 {p.retiree ? 'opacity-45' : ''}">
              <div class="relative aspect-[4/3] overflow-hidden rounded-lg bg-muted">
                <img src={`/api/recidives/${id}/photos/${p.id}`} alt="Photo du {dateLongue(p.date)}" loading="lazy"
                     class="size-full object-cover {p.ancien ? 'grayscale sepia-[.35]' : ''}" />
                <span class="absolute bottom-1 left-1 rounded bg-black/75 px-1.5 text-[0.7rem] text-white">
                  {p.ancien ? 'Ancien scandale' : i === 0 ? 'En une' : 'Récente'} · {dateCourte(p.date)}</span>
              </div>
              <textarea rows="2" class="min-w-0 rounded-lg border bg-background px-2 py-1 font-mono text-sm" maxlength="220" bind:value={p.legende}
                        oninput={toucher} aria-label="Légende de la photo du {dateLongue(p.date)}" disabled={p.retiree}></textarea>
              <button type="button" class="inline-flex items-center gap-1 self-start text-xs text-muted-foreground hover:text-foreground" onclick={() => basculer(p)}>
                {#if p.retiree}<Eye class="size-3.5" aria-hidden="true" />Remettre{:else}<EyeOff class="size-3.5" aria-hidden="true" />Retirer{/if}
              </button>
            </li>
          {:else}
            <li class="text-sm text-muted-foreground">{ed.etat === 'en_preparation' ? 'Recherche des photos dans Immich…' : 'Aucune photo.'}</li>
          {/each}
        </ul>
      </section>

      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Droit de réponse">
        <h2 class="etiquette mb-2">Page 4 · droit de réponse (le mot des hôtes)</h2>
        <textarea class="w-full rounded-lg border bg-background px-3 py-2 font-serif" rows="7" bind:value={mot} oninput={toucher} aria-label="Mot des hôtes"></textarea>
        <p class="mt-1 text-xs text-muted-foreground">Une ligne vide sépare les paragraphes. Signature : « {d.signature} » (Réglages › Le journal). Aucune date de naissance dans ce journal.</p>
      </section>
    </div>

    <aside class="lg:sticky lg:top-6 lg:self-start" aria-label="Aperçu">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 class="etiquette">Aperçu{modifie ? ' (enregistre pour mettre à jour)' : ''}</h2>
        <span class="flex gap-3 text-xs">
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/recidives/${id}/pdf?mode=impose`}><Download class="size-3.5" aria-hidden="true" />PDF à imprimer</a>
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/recidives/${id}/pdf?mode=lecture`}><Download class="size-3.5" aria-hidden="true" />PDF lecture</a>
        </span>
      </div>
      <div class="max-h-[78vh] overflow-y-auto rounded-xl border" bind:clientWidth={largeur}>
        <div style="height:{Math.round(3480 * echelle)}px;position:relative;overflow:hidden">
          <iframe title="Aperçu de La Récidive" src={`/api/recidives/${id}/apercu?mode=ecran&t=${tampon}`} scrolling="no"
                  style="position:absolute;top:0;left:0;width:600px;height:3480px;border:0;transform:scale({echelle});transform-origin:0 0"></iframe>
        </div>
      </div>
      <p class="mt-2 text-xs text-muted-foreground">Impression : A4 paysage, recto-verso bord court, puis plier en deux.</p>
    </aside>
  </div>
{:else if message}
  <p class="text-sm text-destructive" role="alert">{message}</p>
{:else}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}

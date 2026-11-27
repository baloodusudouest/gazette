<script>
  // Écran d'ouverture : les séjours à venir (qui arrive, son livret est-il prêt ?) puis tous les livrets.
  // 0.9 : à partir du 2e séjour, l'invité reçoit La Récidive (journal à scandale) à la place de sa Gazette.
  // 0.24 : plus de « Nouvelle fiche » (les fiches viennent de carnet, à l'annonce de Home Assistant ou depuis
  // À traiter) ; bouton « Séjour annulé » sur un séjour pas encore commencé que Home Assistant n'a pas retiré.
  import { onMount, onDestroy } from 'svelte'
  import Cake from '@lucide/svelte/icons/cake'
  import { api } from '$lib/api.js'
  import Etat from '$lib/Etat.svelte'
  import { dateCourte, dateLongue } from '$lib/format.js'

  let { ondeconnecte } = $props()
  let d = $state(null)
  let erreur = $state('')
  let message = $state('')
  let minuteur = null

  async function lire() {
    try {
      d = await api.get('/api/livrets')
      clearTimeout(minuteur)
      if (d.livrets.some((l) => l.etat === 'en_preparation') || d.recidives.some((r) => r.etat === 'en_preparation')) minuteur = setTimeout(lire, 4000)
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      else erreur = err.message
    }
  }
  const t = new Date()          // 0.24.1 : annulable jusqu'au jour d'arrivée compris
  const aujourdhui = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`
  async function annuler(s) {
    const noms = s.invites.map((i) => i.nom).join(', ')
    if (!confirm(`Séjour annulé : ${noms}, chambre ${s.chambre}, du ${dateCourte(s.du)} ?\n\nSa Récidive est supprimée (même approuvée) ; si l'invité n'a plus de séjour, sa fiche et sa Gazette pas approuvée sont supprimées.`)) return
    message = ''
    try {
      const r = await api.del(`/api/sejours/${s.id}`)
      message = r.annules.length ? `Séjour retiré : ${r.annules.join(', ')}.` : 'Séjour retiré.'
      await lire()
    } catch (err) { message = err.message }
  }
  const parId = $derived(Object.fromEntries((d?.livrets ?? []).map((l) => [l.id, l])))
  onMount(lire)
  onDestroy(() => clearTimeout(minuteur))
</script>

<header class="mb-5">
  <p class="etiquette">Gazette</p>
  <h1 class="titre">Livrets</h1>
</header>

{#if erreur}<p class="mb-4 text-sm text-destructive" role="alert">{erreur}</p>{/if}
{#if message}<p class="mb-4 text-sm text-muted-foreground" role="status">{message}</p>{/if}

{#if d}
  {#if d.sejours.length}
    <section class="mb-8" aria-label="Séjours à venir">
      <h2 class="etiquette mb-3">Séjours à venir</h2>
      <ul class="grid gap-3 md:grid-cols-2">
        {#each d.sejours as s}
          <li class="rounded-2xl border bg-card p-4">
            <p class="flex items-baseline justify-between gap-2">
              <span class="font-medium capitalize">Chambre {s.chambre}</span>
              <span class="text-sm text-muted-foreground">{dateCourte(s.du)} → {dateCourte(s.jusqu_au)}</span>
            </p>
            <ul class="mt-2 grid gap-1.5">
              {#each s.invites as i}
                {@const l = parId[i.personne_id]}
                <li class="flex items-center justify-between gap-2 text-sm">
                  {#if l && i.edition}
                    <a class="underline-offset-4 hover:underline" href={'#/recidive/' + i.edition.id}>{i.nom}</a>
                    <span class="flex items-center gap-2">
                      <span class="text-xs font-semibold tracking-wide text-primary uppercase">La Récidive N° {i.edition.numero}</span>
                      <Etat etat={i.edition.etat} />
                    </span>
                  {:else if l}
                    <a class="underline-offset-4 hover:underline" href={'#/livret/' + l.id}>{i.nom}</a>
                    <span class="flex items-center gap-2">
                      {#if l.anniversaire}<Cake class="size-4 text-primary" aria-label="Anniversaire {l.anniversaire.libelle}" />{/if}
                      <Etat etat={l.etat} />
                    </span>
                  {:else}
                    <span>{i.nom}</span>
                    <a href="#/a-traiter" class="text-xs text-primary">pas de fiche</a>
                  {/if}
                </li>
              {/each}
            </ul>
            {#if s.du >= aujourdhui}
              <p class="mt-3 flex justify-end">
                <button type="button" onclick={() => annuler(s)} class="text-xs text-muted-foreground underline-offset-4 hover:text-destructive hover:underline">Séjour annulé</button>
              </p>
            {/if}
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  {#if d.recidives.length}
    <section class="mb-8" aria-label="La Récidive">
      <h2 class="etiquette mb-3">La Récidive · éditions</h2>
      <ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {#each d.recidives as r}
          <li>
            <a href={'#/recidive/' + r.id} class="flex h-full flex-col gap-2 rounded-2xl border bg-card p-4 transition-colors hover:border-primary">
              <span class="flex items-start justify-between gap-2"><span class="font-medium">{r.nom}</span><Etat etat={r.etat} /></span>
              <span class="text-sm text-muted-foreground">N° {r.numero} · séjour du {dateLongue(r.sejour_du)}</span>
              {#if r.photos}<span class="text-sm">{r.photos} photo{r.photos > 1 ? 's' : ''}{r.anciens ? ` dont ${r.anciens} ancien${r.anciens > 1 ? 's' : ''} scandale${r.anciens > 1 ? 's' : ''}` : ''}</span>{/if}
              {#if r.erreur}<span class="text-xs text-destructive">{r.erreur}</span>{/if}
            </a>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <section aria-label="Tous les livrets">
    <h2 class="etiquette mb-3">Tous les livrets</h2>
    {#if d.archives}<p class="-mt-2 mb-3 text-xs text-muted-foreground">{d.archives} ancien{d.archives > 1 ? 's' : ''} numéro{d.archives > 1 ? 's' : ''} (séjour fini) rangé{d.archives > 1 ? 's' : ''} dans les <a class="underline hover:text-foreground" href="#/archives">Archives</a>.</p>{/if}
    {#if d.livrets.length === 0}
      <p class="text-sm text-muted-foreground">Aucune fiche pour l'instant : elles se créent d'après carnet quand Home Assistant annonce un séjour (ou depuis À traiter).</p>
    {:else}
      <ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Livrets">
        {#each d.livrets as l}
          <li>
            <a href={'#/livret/' + l.id} class="flex h-full flex-col gap-2 rounded-2xl border bg-card p-4 transition-colors hover:border-primary">
              <span class="flex items-start justify-between gap-2">
                <span class="font-medium">{l.nom}</span>
                <Etat etat={l.etat} />
              </span>
              <span class="text-sm text-muted-foreground">né·e le {dateLongue(l.naissance)}</span>
              {#if l.une}<span class="line-clamp-2 font-serif text-sm italic">« {l.une} »</span>{/if}
              {#if l.erreur}<span class="text-xs text-destructive">{l.erreur}</span>{/if}
              {#if l.anniversaire}
                <span class="mt-auto flex items-center gap-1.5 text-xs text-primary"><Cake class="size-3.5" aria-hidden="true" />
                  anniversaire {l.anniversaire.libelle} ({dateCourte(l.anniversaire.anniversaire)})</span>
              {/if}
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
{:else if !erreur}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}

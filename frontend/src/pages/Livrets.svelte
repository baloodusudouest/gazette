<script>
  // Écran d'ouverture : les séjours à venir (qui arrive, son livret est-il prêt ?) puis tous les livrets.
  import { onMount, onDestroy } from 'svelte'
  import Plus from '@lucide/svelte/icons/plus'
  import Cake from '@lucide/svelte/icons/cake'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Etat from '$lib/Etat.svelte'
  import FicheForm from '$lib/FicheForm.svelte'
  import { dateCourte, dateLongue } from '$lib/format.js'

  let { ondeconnecte } = $props()
  let d = $state(null)
  let erreur = $state('')
  let nouvelle = $state(false)
  let minuteur = null

  async function lire() {
    try {
      d = await api.get('/api/livrets')
      clearTimeout(minuteur)
      if (d.livrets.some((l) => l.etat === 'en_preparation')) minuteur = setTimeout(lire, 4000)
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      else erreur = err.message
    }
  }
  async function creer(fiche) {
    const r = await api.post('/api/personnes', fiche)
    location.hash = `#/livret/${r.id}`
  }
  const parId = $derived(Object.fromEntries((d?.livrets ?? []).map((l) => [l.id, l])))
  onMount(lire)
  onDestroy(() => clearTimeout(minuteur))
</script>

<header class="mb-5 flex flex-wrap items-end justify-between gap-3">
  <div>
    <p class="etiquette">Gazette</p>
    <h1 class="titre">Livrets</h1>
  </div>
  <Button onclick={() => (nouvelle = !nouvelle)} variant={nouvelle ? 'outline' : 'default'}>
    <Plus class="size-4" aria-hidden="true" /> Nouvelle fiche
  </Button>
</header>

{#if erreur}<p class="mb-4 text-sm text-destructive" role="alert">{erreur}</p>{/if}

{#if nouvelle}
  <section class="mb-6 rounded-2xl border bg-card p-5" aria-label="Nouvelle fiche">
    <h2 class="mb-1 text-lg font-semibold">Nouvelle fiche</h2>
    <p class="mb-4 text-sm text-muted-foreground">Le livret se prépare aussitôt depuis les sources libres, puis attend ta relecture.</p>
    <FicheForm onvalider={creer} onannuler={() => (nouvelle = false)} />
  </section>
{/if}

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
                  {#if l}
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
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <section aria-label="Tous les livrets">
    <h2 class="etiquette mb-3">Tous les livrets</h2>
    {#if d.livrets.length === 0}
      <p class="text-sm text-muted-foreground">Aucune fiche pour l'instant. Crée la première, ou laisse Home Assistant annoncer un séjour.</p>
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

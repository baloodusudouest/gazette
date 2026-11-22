<script>
  // Navigation commune (format du socle) : rail à gauche sur PC, barre d'icônes collée en bas sur iPhone.
  // Entrées : Livrets (le geste répété), À traiter, Connexion, Réglages. Un livret s'ouvre à #/livret/<id>.
  import { onMount } from 'svelte'
  import { fly } from 'svelte/transition'
  import Newspaper from '@lucide/svelte/icons/newspaper'
  import Inbox from '@lucide/svelte/icons/inbox'
  import Network from '@lucide/svelte/icons/network'
  import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal'
  import Archive from '@lucide/svelte/icons/archive'
  import { api } from '$lib/api.js'
  import Connexion from './pages/Connexion.svelte'
  import Livrets from './pages/Livrets.svelte'
  import Livret from './pages/Livret.svelte'
  import Recidive from './pages/Recidive.svelte'
  import ATraiter from './pages/ATraiter.svelte'
  import Services from '$lib/services/Services.svelte'   // 0.29 : écran commun (contrat 3, socle 0.11.0)
  import Reglages from './pages/Reglages.svelte'
  import Archives from './pages/Archives.svelte'
  import Fiche from './pages/Fiche.svelte'
  import Eurovision from './pages/Eurovision.svelte'

  const onglets = [
    { page: 'livrets', nom: 'Livrets', icone: Newspaper },
    { page: 'archives', nom: 'Archives', icone: Archive },     // 0.20 : anciens numéros
    { page: 'a-traiter', nom: 'À traiter', icone: Inbox },
    { page: 'connexion', nom: 'Connexion', icone: Network },
    { page: 'reglages', nom: 'Réglages', icone: SlidersHorizontal },
  ]

  let connecte = $state(null)
  let session = $state({ version: '', lecture_seule: false, lecture_seule_origine: '' })
  let route = $state(lireRoute())
  let compteur = $state(0)

  function lireRoute() {
    const h = location.hash.replace(/^#\//, '')
    const m = h.match(/^livret\/(\d+)/)
    if (m) return { page: 'livret', id: +m[1] }
    const r = h.match(/^recidive\/(\d+)/)
    if (r) return { page: 'recidive', id: +r[1] }
    // 0.28 : « Good Evening Europe! », l'édition spéciale Eurovision (#/eurovision/<id>)
    const ev = h.match(/^eurovision\/(\d+)/)
    if (ev) return { page: 'eurovision', id: +ev[1] }
    // 0.23 : fiche complète d'une personne (#/fiche/<id>?retour=recidive/<id>)
    const f = h.match(/^fiche\/(\d+)(?:\?retour=([\w/-]+))?/)
    if (f) return { page: 'fiche', id: +f[1], retour: f[2] ?? '' }
    return { page: onglets.some((o) => o.page === h) ? h : 'livrets' }
  }

  async function verifier() {
    try {
      const s = await api.get('/api/session')
      session = s
      connecte = s.connecte
      if (connecte) compter()
    } catch {
      connecte = false
    }
  }
  async function compter() {
    try { compteur = (await api.get('/api/a-traiter')).total } catch { /* sans gravité */ }
  }
  async function deconnecter() {
    try { await api.post('/api/deconnexion') } catch { /* déjà déconnecté */ }
    connecte = false
  }
  const actif = (o) => route.page === o.page || (['livret', 'recidive', 'fiche'].includes(route.page) && o.page === 'livrets') || (route.page === 'eurovision' && o.page === 'a-traiter')

  onMount(verifier)
</script>

<svelte:window onhashchange={() => { route = lireRoute(); compter() }} />

{#if connecte === false}
  <Connexion onconnecte={verifier} />
{:else if connecte}
  <div class="md:pl-52">
    <nav
      aria-label="Sections"
      class="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around gap-1 border-t bg-card/95 px-2 pt-1.5 pb-[calc(0.375rem+env(safe-area-inset-bottom))] backdrop-blur-md
             md:inset-y-0 md:left-0 md:right-auto md:justify-start md:w-52 md:translate-x-0 md:flex-col md:items-stretch md:gap-1 md:rounded-none md:border-0 md:border-r md:bg-transparent md:p-4 md:shadow-none md:backdrop-blur-none"
    >
      <span class="mb-4 hidden px-2 text-xl font-light tracking-tight md:block">Gazette</span>
      {#each onglets as o}
        {@const Icone = o.icone}
        <a
          href={'#/' + o.page}
          aria-label={o.nom}
          aria-current={actif(o) ? 'page' : undefined}
          class="relative flex h-11 items-center gap-2 rounded-full px-4 text-sm font-medium text-muted-foreground transition-colors
                 hover:text-foreground aria-[current=page]:bg-foreground aria-[current=page]:text-background
                 md:h-10 md:rounded-lg md:px-3 md:aria-[current=page]:bg-secondary md:aria-[current=page]:text-foreground"
        >
          <Icone class="size-[1.15rem]" aria-hidden="true" />
          <span class="sr-only md:not-sr-only">{o.nom}</span>
          {#if o.page === 'a-traiter' && compteur > 0}
            <span class="absolute top-1 right-1 rounded-full bg-primary px-1.5 text-[0.65rem] leading-4 font-semibold text-primary-foreground md:static md:ml-auto md:text-xs"
                  aria-label="{compteur} à traiter">{compteur}</span>
          {/if}
        </a>
      {/each}
    </nav>

    <main
      class="mx-auto max-w-6xl px-[max(1rem,env(safe-area-inset-left))] pt-[calc(1.25rem+env(safe-area-inset-top))] pb-[calc(6rem+env(safe-area-inset-bottom))] md:px-8 md:pt-8 md:pb-10"
    >
      {#if session.lecture_seule}
        <p class="mb-4 rounded-xl border border-primary/50 px-4 py-2 text-sm" role="status">
          Mode lecture seule : Gazette prépare et montre les livrets mais n'imprime rien
          ({session.lecture_seule_origine === 'maison' ? 'toute la maison, MAISON_LECTURE_SEULE' : 'cette appli, GAZETTE_LECTURE_SEULE'}).
        </p>
      {/if}
      {#key route.page + (route.id ?? '')}
        <div in:fly={{ y: 6, duration: 180 }}>
          {#if route.page === 'livret'}
            <Livret id={route.id} onchange={compter} ondeconnecte={() => (connecte = false)} />
          {:else if route.page === 'fiche'}
            <Fiche id={route.id} retour={route.retour} ondeconnecte={() => (connecte = false)} />
          {:else if route.page === 'eurovision'}
            <Eurovision id={route.id} onchange={compter} ondeconnecte={() => (connecte = false)} />
          {:else if route.page === 'recidive'}
            <Recidive id={route.id} onchange={compter} ondeconnecte={() => (connecte = false)} />
          {:else if route.page === 'a-traiter'}
            <ATraiter onchange={compter} ondeconnecte={() => (connecte = false)} />
          {:else if route.page === 'connexion'}
            <Services etiquette="Gazette" lectureSeule={session.lecture_seule} ondeconnecte={() => (connecte = false)} />
          {:else if route.page === 'archives'}
            <Archives ondeconnecte={() => (connecte = false)} />
          {:else if route.page === 'reglages'}
            <Reglages {session} {deconnecter} />
          {:else}
            <Livrets ondeconnecte={() => (connecte = false)} />
          {/if}
        </div>
      {/key}
    </main>
  </div>
{/if}

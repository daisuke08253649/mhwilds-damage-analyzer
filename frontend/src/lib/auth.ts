import type { User, Session } from '@supabase/supabase-js'
import { createClient } from '@/lib/supabase'

export async function signIn(
  email: string,
  password: string
): Promise<{ user: User; session: Session } | { error: string }> {
  const supabase = createClient()
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) return { error: error.message }
  return { user: data.user, session: data.session }
}

export async function signUp(
  email: string,
  password: string
): Promise<{ user: User | null } | { error: string }> {
  const supabase = createClient()
  const { data, error } = await supabase.auth.signUp({ email, password })
  if (error) return { error: error.message }
  return { user: data.user }
}

export async function signOut(): Promise<void> {
  const supabase = createClient()
  await supabase.auth.signOut()
}

export async function getUser(): Promise<User | null> {
  const supabase = createClient()
  const { data } = await supabase.auth.getUser()
  return data.user
}

export async function getSession(): Promise<Session | null> {
  const supabase = createClient()
  const { data } = await supabase.auth.getSession()
  return data.session
}

export async function getAccessToken(): Promise<string | null> {
  const session = await getSession()
  return session?.access_token ?? null
}

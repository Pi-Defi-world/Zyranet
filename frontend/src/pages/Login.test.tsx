import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../lib/auth'
import Login from './Login'

const loginMock = vi.fn()

vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>()
  return {
    ...actual,
    api: {
      ...actual.api,
      login: (username: string, password: string) => loginMock(username, password),
      me: () => Promise.reject(new Error('no session')),
    },
  }
})

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  loginMock.mockReset()
  localStorage.clear()
})

describe('Login page', () => {
  it('shows the error message returned by the backend', async () => {
    loginMock.mockRejectedValue(new Error('Invalid username or password'))
    renderLogin()

    await userEvent.type(screen.getByLabelText('Username'), 'admin')
    await userEvent.type(screen.getByLabelText('Password'), 'nope')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Invalid username or password')).toBeInTheDocument()
  })

  it('submits credentials and navigates on success', async () => {
    loginMock.mockResolvedValue(undefined)
    renderLogin()

    await userEvent.type(screen.getByLabelText('Username'), 'admin')
    await userEvent.type(screen.getByLabelText('Password'), 'secret')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(loginMock).toHaveBeenCalledWith('admin', 'secret')
  })
})

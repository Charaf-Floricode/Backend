# backend/manage_users.py
import typer, getpass
from sqlmodel import Session, select
from database import engine
from models import User
from security import hash_password
from database import init_db
from tabulate import tabulate
init_db()   
cli = typer.Typer(help="FloriCODE gebruikersbeheer")

@cli.command()

def add(
    username: str = typer.Argument(...),
    role: str = typer.Option("user", help="Rol van de gebruiker"),
):
    """Voeg een nieuwe gebruiker toe."""
    pwd = getpass.getpass("Password: ")
    with Session(engine) as s:
        if s.exec(select(User).where(User.username == username)).first():
            typer.echo("❌ Bestaat al"); raise typer.Exit(1)
        s.add(User(username=username, hashed_password=hash_password(pwd), role=role))
        s.commit(); typer.echo("✅ Aangemaakt")

@cli.command()
def passwd(username: str):
    """Wachtwoord wijzigen."""
    pwd = getpass.getpass("New password: ")
    with Session(engine) as s:
        user = s.exec(select(User).where(User.username == username)).first()
        if not user: typer.echo("❌ Niet gevonden"); raise typer.Exit(1)
        user.hashed_password = hash_password(pwd)
        s.add(user); s.commit(); typer.echo("🔑 Gewijzigd")

@cli.command()
def delete(username: str):
    """Verwijder een gebruiker."""
    with Session(engine) as s:
        user = s.exec(select(User).where(User.username == username)).first()
        if not user: typer.echo("❌ Niet gevonden"); raise typer.Exit(1)
        s.delete(user); s.commit(); typer.echo("🗑️  Verwijderd")
@cli.command()
def list(
    full: bool = typer.Option(False, help="Toon hashes erbij"),
    show_role: bool = typer.Option(True, help="Toon de role-kolom"),  # nieuw
):
    """Lijst alle gebruikers (id, username, role, optioneel hash)."""
    from tabulate import tabulate           # pip install tabulate als je dit nog niet hebt
    cols = [User.id, User.username]                     # basis
    headers = ["id", "username"]

    if show_role:
        cols.append(User.role)
        headers.append("role")

    if full:                                           # hashes apart
        cols.append(User.hashed_password)
        headers.append("hashed_password")

    with Session(engine) as s:
        rows = s.exec(select(*cols)).all()

    print(tabulate(rows, headers=headers))

if __name__ == "__main__":
    cli()

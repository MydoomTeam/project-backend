/*==============================================================*/
/* DBMS name:      PostgreSQL 9.x                               */
/* Created on:     28/04/2026 12:27:05 a. m.                    */
/*==============================================================*/

/*==============================================================*/
/* Table: ADMINISTRADOR                                         */
/*==============================================================*/
create table ADMINISTRADOR (
   ID                   INT4                 not null,
   NOMBRE_USUARIO       TEXT                 not null,
   CORREO_ELECTRONICO   TEXT                 not null,
   CONTRASENA_HASH      TEXT                 not null,
   ROL                  TEXT                 not null,
   FECHA_ULTIMO_ACCESO  DATE                 not null,
   constraint PK_ADMINISTRADOR primary key (ID)
);

create unique index ADMINISTRADOR_PK on ADMINISTRADOR (
   ID
);

/*==============================================================*/
/* Table: JUGADOR                                               */
/*==============================================================*/
create table JUGADOR (
   ID                   INT4                 not null,
   NOMBRE_USUARIO       TEXT                 not null,
   CORREO_ELECTRONICO   TEXT                 not null,
   CONTRASENA_HASH      TEXT                 not null,
   ROL                  TEXT                 not null,
   FECHA_ULTIMO_ACCESO  DATE                 not null,
   ELO_GLOBAL           INT4                 not null,
   constraint PK_JUGADOR primary key (ID)
);

create unique index JUGADOR_PK on JUGADOR (
   ID
);

/*==============================================================*/
/* Table: TORNEO                                                */
/*==============================================================*/
create table TORNEO (
   ID                   INT4                 not null,
   ADMINISTRADOR_ID     INT4                 not null,
   NOMBRE               TEXT                 not null,
   TIPO_ELIMINACION     TEXT                 not null,
   NOMBRE_JUEGO         TEXT                 not null,
   CATEGORIA_JUEGO      TEXT                 not null,
   NUMERO_PARTICIPANTES INT4                 not null,
   NUMERO_RONDAS        INT4                 not null,
   DURACION_RONDA       INT4                 not null,
   ESTADO               TEXT                 not null,
   FECHA_INICIO         DATE                 not null,
   FECHA_FIN            DATE                 null,
   IDIOMA               TEXT                 null,
   REGION               TEXT                 null,
   constraint PK_TORNEO primary key (ID)
);

create unique index TORNEO_PK on TORNEO (
   ID
);

/*==============================================================*/
/* Table: RONDA                                                 */
/*==============================================================*/
create table RONDA (
   ID                   INT4                 not null,
   TORNEO_ID            INT4                 not null,
   NUMERO_FASE          INT4                 not null,
   constraint PK_RONDA primary key (ID)
);

create unique index RONDA_PK on RONDA (
   ID
);

/*==============================================================*/
/* Table: INSCRIPCION                                           */
/*==============================================================*/
create table INSCRIPCION (
   ID                   INT4                 not null,
   TORNEO_ID            INT4                 not null,
   JUGADOR_ID           INT4                 not null,
   ESTADO_PARTICIPANTE  TEXT                 not null,
   FECHA_INSCRIPCION    DATE                 not null,
   ELO_SEED             INT4                 null,
   constraint PK_INSCRIPCION primary key (ID)
);

create unique index INSCRIPCION_PK on INSCRIPCION (
   ID
);

/*==============================================================*/
/* Table: ENFRENTAMIENTO                                        */
/*==============================================================*/
create table ENFRENTAMIENTO (
   ID                   INT4                 not null,
   RONDA_ID             INT4                 not null,
   INSCRIPCION_A_ID     INT4                 not null,
   INSCRIPCION_B_ID     INT4                 not null,
   MATCH_SIGUIENTE_ID   INT4                 null,
   ESTADO_MATCH         TEXT                 not null,
   MARCADOR_DETALLE     TEXT                 not null,
   FECHA_HORA_PROGRAMADA DATE                 not null,
   RESULTADO            TEXT                 null,
   constraint PK_ENFRENTAMIENTO primary key (ID)
);

create unique index ENFRENTAMIENTO_PK on ENFRENTAMIENTO (
   ID
);

/*==============================================================*/
/* Table: HISTORIALELO                                          */
/*==============================================================*/
create table HISTORIALELO (
   ID                   INT4                 not null,
   ENFRENTAMIENTO_ID    INT4                 not null,
   JUGADOR_ID           INT4                 not null,
   VALOR_ELO_ANTERIOR   INT4                 not null,
   VALOR_ELO_ACTUAL     INT4                 not null,
   FECHA_CAMBIO         DATE                 not null,
   constraint PK_HISTORIALELO primary key (ID)
);

create unique index HISTORIALELO_PK on HISTORIALELO (
   ID
);

/*==============================================================*/
/* Table: LOGAUDITORIA                                          */
/*==============================================================*/
create table LOGAUDITORIA (
   ID                   INT4                 not null,
   ADMINISTRADOR_ID     INT4                 not null,
   ACCION               TEXT                 not null,
   "TIMESTAMP"          DATE                 not null,
   DESCRIPCION_CAMBIO   TEXT                 null,
   constraint PK_LOGAUDITORIA primary key (ID)
);

create unique index LOGAUDITORIA_PK on LOGAUDITORIA (
   ID
);

/*==============================================================*/
/* Table: ALERTA                                                */
/*==============================================================*/
create table ALERTA (
   ID                   INT4                 not null,
   ADMINISTRADOR_ID     INT4                 null,
   JUGADOR_ID           INT4                 null,
   TIPO_EVENTO          TEXT                 not null,
   MENSAJE              TEXT                 not null,
   FECHA_HORA           DATE                 not null,
   ESTADO_LECTURA       TEXT                 not null,
   constraint PK_ALERTA primary key (ID)
);

create unique index ALERTA_PK on ALERTA (
   ID
);

alter table ALERTA
   add constraint FK_ALERTA_ADMINISTRADOR_ID foreign key (ADMINISTRADOR_ID)
      references ADMINISTRADOR (ID)
      on delete restrict on update restrict;

alter table ALERTA
   add constraint FK_ALERTA_JUGADOR_ID foreign key (JUGADOR_ID)
      references JUGADOR (ID)
      on delete restrict on update restrict;

alter table ENFRENTAMIENTO
   add constraint FK_ENFRENTAMIENTO_RONDA_ID foreign key (RONDA_ID)
      references RONDA (ID)
      on delete restrict on update restrict;

alter table ENFRENTAMIENTO
   add constraint FK_ENFRENTAMIENTO_INSCRIPCION_A_ID foreign key (INSCRIPCION_A_ID)
      references INSCRIPCION (ID)
      on delete restrict on update restrict;

alter table ENFRENTAMIENTO
   add constraint FK_ENFRENTAMIENTO_INSCRIPCION_B_ID foreign key (INSCRIPCION_B_ID)
      references INSCRIPCION (ID)
      on delete restrict on update restrict;

alter table ENFRENTAMIENTO
   add constraint FK_ENFRENTAMIENTO_MATCH_SIGUIENTE_ID foreign key (MATCH_SIGUIENTE_ID)
      references ENFRENTAMIENTO (ID)
      on delete restrict on update restrict;

alter table HISTORIALELO
   add constraint FK_HISTORIALELO_ENFRENTAMIENTO_ID foreign key (ENFRENTAMIENTO_ID)
      references ENFRENTAMIENTO (ID)
      on delete restrict on update restrict;

alter table HISTORIALELO
   add constraint FK_HISTORIALELO_JUGADOR_ID foreign key (JUGADOR_ID)
      references JUGADOR (ID)
      on delete restrict on update restrict;

alter table INSCRIPCION
   add constraint FK_INSCRIPCION_TORNEO_ID foreign key (TORNEO_ID)
      references TORNEO (ID)
      on delete restrict on update restrict;

alter table INSCRIPCION
   add constraint FK_INSCRIPCION_JUGADOR_ID foreign key (JUGADOR_ID)
      references JUGADOR (ID)
      on delete restrict on update restrict;

alter table LOGAUDITORIA
   add constraint FK_LOGAUDITORIA_ADMINISTRADOR_ID foreign key (ADMINISTRADOR_ID)
      references ADMINISTRADOR (ID)
      on delete restrict on update restrict;

alter table RONDA
   add constraint FK_RONDA_TORNEO_ID foreign key (TORNEO_ID)
      references TORNEO (ID)
      on delete restrict on update restrict;

alter table TORNEO
   add constraint FK_TORNEO_ADMINISTRADOR_ID foreign key (ADMINISTRADOR_ID)
      references ADMINISTRADOR (ID)
      on delete restrict on update restrict;
